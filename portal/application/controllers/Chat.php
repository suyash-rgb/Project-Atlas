<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * Chat Controller
 * 
 * Handles incoming chat interactions from the legacy web portal,
 * renders the copilot interface, routes queries through Atlas_client,
 * and records user feedback in the database.
 */
class Chat extends CI_Controller {

    public function __construct() {
        parent::__construct();
        $this->load->library('atlas_client');
        $this->load->library('session');
        $this->load->helper(array('url', 'form', 'security'));
        if (getenv('DB_HOST')) {
            $this->load->database();
        }
    }

    /**
     * Display the Copilot Web Interface
     */
    public function index() {
        $data['title'] = 'Report Copilot | Cognitive Market Research';
        
        $data['client'] = $this->session->userdata('client_auth');

        $this->load->view('chat_view', $data);
    }

    /**
     * AJAX endpoint to handle chat messages
     */
    public function send() {
        // Enforce JSON POST
        if (!$this->input->is_ajax_request() && $this->input->method() !== 'post') {
            show_404();
            return;
        }

        $client = $this->authenticated_client();
        if (!$client) {
            return;
        }

        $raw_input = file_get_contents('php://input');
        $input = json_decode($raw_input, true);
        if (!is_array($input)) {
            $input = $this->input->post();
        }

        $query = is_array($input) && isset($input['query']) && is_string($input['query'])
            ? trim($input['query'])
            : '';

        if (empty($query)) {
            $this->json_error(400, 'Query cannot be empty.');
            return;
        }

        // Send query to Python FastAPI service via Atlas_client
        $history = $this->load_recent_conversation_history($client['id']);
        if ($history === false) {
            $this->json_error(503, 'Conversation context is temporarily unavailable.');
            return;
        }
        $response = $this->atlas_client->send_chat($client['id'], $query, $history);

        // Persist conversation if database is active and response succeeded
        if (isset($this->db) && isset($this->db->conn_id) && $this->db->conn_id && isset($response['data'])) {
            $data_payload = $response['data'];
            if (!$this->db->insert('conversations', array(
                'session_id' => $this->session->userdata('conversation_session_id'),
                'client_id'  => $client['id'],
                'question'   => $query,
                'answer'     => isset($data_payload['answer']) ? $data_payload['answer'] : '',
                'confidence' => isset($data_payload['confidence']) ? (float)$data_payload['confidence'] : 1.0,
                'escalated'  => !empty($data_payload['escalated']) ? 1 : 0,
                'created_at' => date('Y-m-d H:i:s')
            ))) {
                log_message('error', 'Failed to persist a completed chat conversation.');
            }
        }

        $this->output
            ->set_content_type('application/json')
            ->set_status_header($response['code'])
            ->set_output(json_encode($response));
    }

    /**
     * AJAX endpoint that streams chat tokens through the PHP portal.
     */
    public function stream() {
        if (!$this->input->is_ajax_request() && $this->input->method() !== 'post') {
            show_404();
            return;
        }

        $client = $this->authenticated_client();
        if (!$client) {
            return;
        }

        $input = json_decode(file_get_contents('php://input'), true);
        if (!is_array($input)) {
            $input = $this->input->post();
        }
        if (!is_array($input)) {
            $this->output
                ->set_content_type('application/json')
                ->set_status_header(400)
                ->set_output(json_encode(array(
                    'status' => 'error',
                    'message' => 'Invalid JSON request.'
                )));
            return;
        }

        $query = isset($input['query']) && is_string($input['query'])
            ? trim($input['query'])
            : '';

        if ($query === '') {
            $this->json_error(400, 'Query cannot be empty.');
            return;
        }

        $history = $this->load_recent_conversation_history($client['id']);
        if ($history === false) {
            $this->json_error(503, 'Conversation context is temporarily unavailable.');
            return;
        }
        $this->atlas_client->stream_chat($client['id'], $query, $history);
    }

    private function load_recent_conversation_history($client_id) {
        $session_id = $this->session->userdata('conversation_session_id');
        if (
            !isset($this->db)
            || !isset($this->db->conn_id)
            || !$this->db->conn_id
            || !$session_id
        ) {
            return array();
        }

        $query = $this->db
            ->select('question, answer')
            ->from('conversations')
            ->where('session_id', $session_id)
            ->where('client_id', $client_id)
            ->order_by('id', 'DESC')
            ->limit(4)
            ->get();
        if ($query === false) {
            log_message('error', 'Failed to load recent conversation context.');
            return false;
        }

        $rows = $query->result_array();

        foreach ($rows as &$row) {
            $row['question'] = $this->limit_history_text($row['question']);
            $row['answer'] = $this->limit_history_text($row['answer']);
        }
        unset($row);
        $rows = array_reverse($rows);

        $history = array();
        foreach ($rows as $row) {
            if ($row['question'] !== '') {
                $history[] = array('role' => 'user', 'content' => $row['question']);
            }
            if ($row['answer'] !== '') {
                $history[] = array('role' => 'assistant', 'content' => $row['answer']);
            }
        }
        return $history;
    }

    private function limit_history_text($text) {
        $text = (string) $text;
        if (preg_match('/\A.{0,2000}/us', $text, $matches) === 1) {
            return $matches[0];
        }
        return substr($text, 0, 2000);
    }

    public function reports() {
        $client = $this->authenticated_client();
        if (!$client) {
            return;
        }

        $response = $this->atlas_client->get_client_reports($client['id']);
        $this->output
            ->set_content_type('application/json')
            ->set_status_header($response['code'])
            ->set_output(json_encode(
                isset($response['data'])
                    ? $response['data']
                    : array('message' => $response['message'])
            ));
    }

    /**
     * AJAX endpoint to persist completed streamed conversation history.
     */
    public function record_conversation() {
        if (!$this->input->is_ajax_request() && $this->input->method() !== 'post') {
            show_404();
            return;
        }

        $client = $this->authenticated_client();
        if (!$client) {
            return;
        }

        $input = json_decode(file_get_contents('php://input'), true);
        if (!is_array($input)) {
            $input = $this->input->post();
        }

        $question = isset($input['question']) ? $this->security->xss_clean($input['question']) : '';
        $answer = isset($input['answer']) ? $this->security->xss_clean($input['answer']) : '';
        $confidence = isset($input['confidence']) ? (float)$input['confidence'] : 1.0;
        $escalated = !empty($input['escalated']) ? 1 : 0;
        $session_id = $this->session->userdata('conversation_session_id');

        if (!isset($this->db) || !isset($this->db->conn_id) || !$this->db->conn_id) {
            $this->json_error(503, 'Conversation storage is unavailable.');
            return;
        }

        if ($question === '' || !$this->db->insert('conversations', array(
            'session_id' => $session_id,
            'client_id'  => $client['id'],
            'question'   => $question,
            'answer'     => $answer,
            'confidence' => $confidence,
            'escalated'  => $escalated,
            'created_at' => date('Y-m-d H:i:s')
        ))) {
            log_message('error', 'Failed to persist a completed chat conversation.');
            $this->json_error(500, 'The conversation could not be saved.');
            return;
        }

        $this->output
            ->set_content_type('application/json')
            ->set_output(json_encode(array('status' => 'success')));
    }

    /**
     * AJAX endpoint to record thumbs-up / thumbs-down user feedback
     */
    public function feedback() {
        if (!$this->input->is_ajax_request() && $this->input->method() !== 'post') {
            show_404();
            return;
        }

        $client = $this->authenticated_client();
        if (!$client) {
            return;
        }

        $raw_input = file_get_contents('php://input');
        $input = json_decode($raw_input, true);
        if (!is_array($input)) {
            $input = $this->input->post();
        }

        $message_id = isset($input['message_id']) ? $this->security->xss_clean($input['message_id']) : ('msg-' . time());
        $rating = isset($input['rating']) ? $this->security->xss_clean($input['rating']) : 'up';
        $query = isset($input['query']) ? $this->security->xss_clean($input['query']) : '';
        $comment = isset($input['comment']) ? $this->security->xss_clean($input['comment']) : '';

        if (!in_array($rating, array('up', 'down'), true) || $query === '') {
            $this->json_error(400, 'Feedback rating and question are required.');
            return;
        }

        if (!isset($this->db) || !isset($this->db->conn_id) || !$this->db->conn_id) {
            $this->json_error(503, 'Feedback storage is unavailable.');
            return;
        }

        $inserted = $this->db->insert('feedback', array(
            'client_id'  => $client['id'],
            'message_id' => $message_id,
            'rating'     => $rating,
            'query'      => $query,
            'comment'    => $comment,
            'created_at' => date('Y-m-d H:i:s')
        ));

        if (!$inserted) {
            log_message('error', 'Failed to insert feedback into MySQL.');
            $this->json_error(500, 'Failed to save feedback.');
            return;
        }

        $this->output
            ->set_content_type('application/json')
            ->set_output(json_encode(array(
                'status'  => 'success',
                'message' => 'Thank you for your feedback!'
            )));
    }

    private function authenticated_client() {
        $client = $this->session->userdata('client_auth');
        if (
            is_array($client)
            && !empty($client['id'])
            && !empty($client['company'])
            && !empty($client['email'])
        ) {
            return $client;
        }

        $this->json_error(401, 'Please sign in to continue.');
        return NULL;
    }

    private function json_error($status, $message) {
        $this->output
            ->set_content_type('application/json')
            ->set_status_header($status)
            ->set_output(json_encode(array(
                'status' => 'error',
                'message' => $message
            )));
    }
}

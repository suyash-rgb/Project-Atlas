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
        $this->load->helper(array('url', 'form', 'security'));
        // Try loading database if configured; fallback gracefully if running standalone
        $this->load->database('', TRUE);
    }

    /**
     * Display the Copilot Web Interface
     */
    public function index() {
        $data['title'] = 'Report Copilot | Cognitive Market Research';
        
        // Mock list of clients for the selector
        $data['clients'] = array(
            'C-01' => 'Global Water Solutions (All Reports)',
            'C-02' => 'City of Austin Water Utility (R-101, R-103)',
            'C-03' => 'AquaTech Industrial Corp (R-104, R-106)',
            'C-04' => 'Blue Delta Infrastructure (R-101 only)',
            'C-05' => 'Northwind Utilities (R-105)',
            'C-06' => 'Public Visitor (Public Excerpts only)'
        );

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

        $raw_input = file_get_contents('php://input');
        $input = json_decode($raw_input, true);

        $client_id = isset($input['client_id']) ? $this->security->xss_clean($input['client_id']) : 'C-01';
        $query = isset($input['query']) ? trim($input['query']) : '';

        if (empty($query)) {
            $this->output
                ->set_content_type('application/json')
                ->set_status_header(400)
                ->set_output(json_encode(array(
                    'status' => 'error',
                    'message' => 'Query cannot be empty.'
                )));
            return;
        }

        // Send query to Python FastAPI service via Atlas_client
        $response = $this->atlas_client->send_chat($client_id, $query);

        $this->output
            ->set_content_type('application/json')
            ->set_status_header($response['code'])
            ->set_output(json_encode($response));
    }

    /**
     * AJAX endpoint to record thumbs-up / thumbs-down user feedback
     */
    public function feedback() {
        if (!$this->input->is_ajax_request() && $this->input->method() !== 'post') {
            show_404();
            return;
        }

        $raw_input = file_get_contents('php://input');
        $input = json_decode($raw_input, true);

        $client_id = isset($input['client_id']) ? $this->security->xss_clean($input['client_id']) : 'C-01';
        $query = isset($input['query']) ? $this->security->xss_clean($input['query']) : '';
        $rating = isset($input['rating']) ? (int)$input['rating'] : 1; // 1 = up, 0 = down
        $comments = isset($input['comments']) ? $this->security->xss_clean($input['comments']) : '';

        // If database connection is active, insert into feedback table
        if ($this->db && $this->db->conn_id) {
            $this->db->insert('feedback', array(
                'client_id' => $client_id,
                'query'     => $query,
                'rating'    => $rating,
                'comments'  => $comments,
                'timestamp' => date('Y-m-d H:i:s')
            ));
        }

        $this->output
            ->set_content_type('application/json')
            ->set_output(json_encode(array(
                'status'  => 'success',
                'message' => 'Thank you for your feedback!'
            )));
    }
}

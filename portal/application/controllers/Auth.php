<?php
defined('BASEPATH') OR exit('No direct script access allowed');

class Auth extends CI_Controller {

    public function __construct() {
        parent::__construct();
        $this->load->database();
        $this->load->library('session');
        $this->load->model('client_account_model');
    }

    public function register() {
        if (!$this->require_post()) {
            return;
        }

        $input = $this->read_json();
        if ($input === NULL) {
            return;
        }

        $company = isset($input['company']) && is_string($input['company'])
            ? trim($input['company'])
            : '';
        $email = isset($input['email']) && is_string($input['email'])
            ? strtolower(trim($input['email']))
            : '';
        $password = isset($input['password']) && is_string($input['password'])
            ? $input['password']
            : '';
        $password_confirmation = isset($input['password_confirmation']) && is_string($input['password_confirmation'])
            ? $input['password_confirmation']
            : '';

        if ($company === '' || strlen($company) > 255) {
            $this->respond(400, array('message' => 'Enter a company name (up to 255 characters).'));
            return;
        }
        if (strlen($email) > 254 || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
            $this->respond(400, array('message' => 'Enter a valid business email address.'));
            return;
        }
        if (strlen($password) < 12 || strlen($password) > 72) {
            $this->respond(400, array('message' => 'Choose a password between 12 and 72 characters.'));
            return;
        }
        if ($password !== $password_confirmation) {
            $this->respond(400, array('message' => 'The passwords do not match.'));
            return;
        }

        $result = $this->client_account_model->create_account(
            $company,
            $email,
            password_hash($password, PASSWORD_DEFAULT)
        );

        if ($result['status'] === 'duplicate') {
            $this->respond(409, array('message' => 'An account already exists for this business email.'));
            return;
        }
        if ($result['status'] !== 'created') {
            $this->respond(500, array('message' => 'Your account could not be created. Please try again.'));
            return;
        }

        $this->start_client_session($result);
        $this->respond(201, array(
            'status' => 'success',
            'client' => $this->public_client($result)
        ));
    }

    public function login() {
        if (!$this->require_post()) {
            return;
        }

        $input = $this->read_json();
        if ($input === NULL) {
            return;
        }

        $email = isset($input['email']) && is_string($input['email'])
            ? strtolower(trim($input['email']))
            : '';
        $password = isset($input['password']) && is_string($input['password'])
            ? $input['password']
            : '';

        if (strlen($email) > 254 || !filter_var($email, FILTER_VALIDATE_EMAIL) || $password === '') {
            $this->respond(400, array('message' => 'Enter your business email and password.'));
            return;
        }

        $account = $this->client_account_model->find_by_email($email);
        if (!$account || !password_verify($password, $account['password_hash'])) {
            $this->respond(401, array('message' => 'The business email or password is incorrect.'));
            return;
        }

        $this->start_client_session($account);
        $this->respond(200, array(
            'status' => 'success',
            'client' => $this->public_client($account)
        ));
    }

    public function logout() {
        if (!$this->require_post()) {
            return;
        }

        $this->session->unset_userdata(array('client_auth', 'conversation_session_id'));
        $this->session->sess_regenerate(TRUE);
        $this->respond(200, array('status' => 'success'));
    }

    private function require_post() {
        if ($this->input->method() === 'post') {
            return TRUE;
        }

        $this->respond(405, array('message' => 'This endpoint requires a POST request.'));
        return FALSE;
    }

    private function read_json() {
        $input = json_decode(file_get_contents('php://input'), TRUE);
        if (is_array($input)) {
            return $input;
        }

        $input = $this->input->post();
        if (is_array($input)) {
            return $input;
        }

        $this->respond(400, array('message' => 'Invalid request.'));
        return NULL;
    }

    private function start_client_session($account) {
        $this->session->sess_regenerate(TRUE);
        $this->session->set_userdata('client_auth', $this->public_client($account));
        $this->session->set_userdata('conversation_session_id', bin2hex(random_bytes(16)));
    }

    private function public_client($account) {
        return array(
            'id' => $account['client_id'],
            'company' => $account['company'],
            'email' => $account['email']
        );
    }

    private function respond($status, $body) {
        $this->output
            ->set_content_type('application/json')
            ->set_status_header($status)
            ->set_output(json_encode($body));
    }
}

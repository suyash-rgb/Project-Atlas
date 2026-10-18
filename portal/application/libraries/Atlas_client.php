<?php
defined('BASEPATH') OR exit('No direct script access allowed');

/**
 * Atlas_client
 * 
 * Reusable HTTP client library to interface between CodeIgniter 3
 * and the Project Atlas Python FastAPI / LangGraph backend.
 */
class Atlas_client {

    protected $CI;
    protected $api_base_url;
    protected $api_key;
    protected $timeout;

    public function __construct() {
        $this->CI =& get_instance();
        
        // Read configuration from environment or config file
        $this->api_base_url = getenv('FASTAPI_URL') ? getenv('FASTAPI_URL') : 'http://api:8000';
        $this->api_key = getenv('ATLAS_API_KEY') ? getenv('ATLAS_API_KEY') : 'atlas_secret_token_2026';
        $this->timeout = 30; // 30-second per-request budget per assignment requirements
    }

    /**
     * Check backend service health
     */
    public function check_health() {
        return $this->_send_request('/health', 'GET');
    }

    /**
     * Send a query to the Report Copilot
     *
     * @param string $client_id  Client identifier (e.g. C-01, C-02)
     * @param string $query      The question text
     * @return array
     */
    public function send_chat($client_id, $query) {
        $payload = array(
            'client_id' => $client_id,
            'query'     => $query
        );
        return $this->_send_request('/api/v1/chat', 'POST', $payload);
    }

    /**
     * Internal cURL helper with strict error and timeout management
     */
    private function _send_request($endpoint, $method = 'GET', $data = null) {
        $url = rtrim($this->api_base_url, '/') . $endpoint;
        $ch = curl_init();

        $headers = array(
            'Content-Type: application/json',
            'Accept: application/json',
            'X-API-Key: ' . $this->api_key
        );

        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, $this->timeout);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);

        if ($method === 'POST') {
            curl_setopt($ch, CURLOPT_POST, true);
            if ($data !== null) {
                curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
            }
        }

        $response = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $curl_error = curl_error($ch);
        curl_close($ch);

        if ($response === false) {
            log_message('error', "Atlas_client cURL failed: {$curl_error} on {$url}");
            return array(
                'status'  => 'error',
                'code'    => 504,
                'message' => 'The Report Copilot service did not respond within the 30-second window. An analyst has been notified.'
            );
        }

        $decoded = json_decode($response, true);
        if ($http_code >= 400) {
            log_message('error', "Atlas_client HTTP {$http_code}: {$response}");
            return array(
                'status'  => 'error',
                'code'    => $http_code,
                'message' => isset($decoded['detail']) ? $decoded['detail'] : 'Backend processing error.',
                'raw'     => $decoded
            );
        }

        return array(
            'status' => 'success',
            'code'   => $http_code,
            'data'   => $decoded
        );
    }
}

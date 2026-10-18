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

        $this->api_base_url = getenv('FASTAPI_URL');
        $this->api_key = getenv('ATLAS_API_KEY');
        if (!$this->api_base_url || !$this->api_key) {
            throw new RuntimeException('FASTAPI_URL and ATLAS_API_KEY must be configured.');
        }
        $url_parts = parse_url($this->api_base_url);
        if (
            !filter_var($this->api_base_url, FILTER_VALIDATE_URL)
            || !is_array($url_parts)
            || !isset($url_parts['scheme'], $url_parts['host'])
            || !in_array(strtolower($url_parts['scheme']), array('http', 'https'), true)
        ) {
            throw new RuntimeException('FASTAPI_URL must be an absolute HTTP or HTTPS URL.');
        }

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
        if ($ch === false) {
            log_message('error', 'Atlas_client could not initialize cURL.');
            return array(
                'status'  => 'error',
                'code'    => 503,
                'message' => 'The Report Copilot service is temporarily unavailable.'
            );
        }

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
            log_message('error', "Atlas_client cURL request failed: {$curl_error}");
            return array(
                'status'  => 'error',
                'code'    => 504,
                'message' => 'The Report Copilot service did not respond within the 30-second window. An analyst has been notified.'
            );
        }

        $decoded = json_decode($response, true);
        if ($http_code >= 400) {
            log_message('error', "Atlas_client received HTTP {$http_code}.");
            return array(
                'status'  => 'error',
                'code'    => $http_code,
                'message' => isset($decoded['detail']) ? $decoded['detail'] : 'Backend processing error.'
            );
        }

        return array(
            'status' => 'success',
            'code'   => $http_code,
            'data'   => $decoded
        );
    }
}

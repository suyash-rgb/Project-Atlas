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

        $this->api_base_url = getenv('FASTAPI_URL') ?: 'http://127.0.0.1:8085';
        $this->api_key = getenv('ATLAS_API_KEY') ?: 'atlas_dev_secret_key';
        $url_parts = parse_url($this->api_base_url);
        if (
            !filter_var($this->api_base_url, FILTER_VALIDATE_URL)
            || !is_array($url_parts)
            || !isset($url_parts['scheme'], $url_parts['host'])
            || !in_array(strtolower($url_parts['scheme']), array('http', 'https'), true)
        ) {
            log_message('error', 'Atlas_client FASTAPI_URL must be an absolute HTTP or HTTPS URL.');
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
     * Relay the FastAPI Server-Sent Events response to the browser without buffering.
     */
    public function stream_chat($client_id, $query) {
        $url = rtrim($this->api_base_url, '/') . '/api/v1/chat/stream';
        $payload = json_encode(array(
            'client_id' => $client_id,
            'query'     => $query
        ));

        if ($payload === false) {
            log_message('error', 'Atlas_client could not encode the streaming request.');
            $this->_send_stream_error(500, 'Could not encode the chat request.');
            return;
        }

        $ch = curl_init();
        if ($ch === false) {
            log_message('error', 'Atlas_client could not initialize cURL for streaming.');
            $this->_send_stream_error(503, 'The Report Copilot service is temporarily unavailable.');
            return;
        }

        while (ob_get_level() > 0) {
            ob_end_clean();
        }
        ob_implicit_flush(true);

        $http_code = 0;
        $content_type = 'text/event-stream';
        $request_id = '';
        $headers_sent = false;

        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
        curl_setopt($ch, CURLOPT_TIMEOUT, 120);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array(
            'Content-Type: application/json',
            'Accept: text/event-stream',
            'X-API-Key: ' . $this->api_key
        ));
        curl_setopt($ch, CURLOPT_HEADERFUNCTION, function ($curl, $header) use (&$http_code, &$content_type, &$request_id, &$headers_sent) {
            $length = strlen($header);
            if (preg_match('/^HTTP\/\S+\s+(\d+)/i', $header, $matches)) {
                $http_code = (int)$matches[1];
            } elseif (stripos($header, 'Content-Type:') === 0) {
                $content_type = trim(substr($header, strlen('Content-Type:')));
            } elseif (stripos($header, 'X-Request-ID:') === 0) {
                $candidate = trim(substr($header, strlen('X-Request-ID:')));
                if (preg_match('/^[a-f0-9-]{16,64}$/i', $candidate)) {
                    $request_id = $candidate;
                }
            } elseif (trim($header) === '' && $http_code > 0 && !$headers_sent) {
                http_response_code($http_code);
                header('Content-Type: ' . $content_type);
                header('Cache-Control: no-cache, no-transform');
                header('X-Accel-Buffering: no');
                if ($request_id !== '') {
                    header('X-Request-ID: ' . $request_id);
                }
                if ($http_code >= 400) {
                    log_message(
                        'error',
                        'Atlas_client stream upstream failed: endpoint=/api/v1/chat/stream status='
                            . $http_code . ' request_id=' . ($request_id !== '' ? $request_id : 'unavailable')
                    );
                }
                $headers_sent = true;
            }
            return $length;
        });
        curl_setopt($ch, CURLOPT_WRITEFUNCTION, function ($curl, $chunk) use (&$headers_sent, &$http_code, &$content_type, &$request_id) {
            if (!$headers_sent) {
                http_response_code($http_code > 0 ? $http_code : 502);
                header('Content-Type: ' . $content_type);
                header('Cache-Control: no-cache, no-transform');
                header('X-Accel-Buffering: no');
                if ($request_id !== '') {
                    header('X-Request-ID: ' . $request_id);
                }
                $headers_sent = true;
            }
            echo $chunk;
            flush();
            return strlen($chunk);
        });

        $result = curl_exec($ch);
        $curl_error = curl_error($ch);
        curl_close($ch);

        if ($result === false) {
            log_message('error', "Atlas_client streaming cURL request failed: {$curl_error}");
            if (!$headers_sent) {
                $this->_send_stream_error(502, 'The Report Copilot service could not be reached.');
            } else {
                echo "event: error\ndata: {\"message\":\"The connection to Report Copilot was interrupted.\"}\n\n";
                flush();
            }
        }
    }

    private function _send_stream_error($code, $message) {
        http_response_code($code);
        header('Content-Type: application/json');
        header('Cache-Control: no-cache');
        echo json_encode(array('status' => 'error', 'message' => $message));
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
            log_message('error', "Atlas_client upstream request failed: endpoint={$endpoint} status={$http_code}.");
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

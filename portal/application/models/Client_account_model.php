<?php
defined('BASEPATH') OR exit('No direct script access allowed');

class Client_account_model extends CI_Model {

    public function find_by_email($email) {
        $query = $this->db
            ->select('client_accounts.client_id, client_accounts.email, client_accounts.password_hash, clients.company')
            ->from('client_accounts')
            ->join('clients', 'clients.id = client_accounts.client_id')
            ->where('client_accounts.email', $email)
            ->limit(1)
            ->get();

        return $query->row_array();
    }

    public function create_account($company, $email, $password_hash) {
        $existing_account = $this->db
            ->where('email', $email)
            ->limit(1)
            ->get('client_accounts')
            ->row_array();
        $existing_client = $this->db
            ->where('contact_email', $email)
            ->limit(1)
            ->get('clients')
            ->row_array();

        if ($existing_account || $existing_client) {
            return array('status' => 'duplicate');
        }

        $client_id = 'C-' . strtoupper(bin2hex(random_bytes(8)));
        $this->db->trans_begin();

        $client_created = $this->db->insert('clients', array(
            'id' => $client_id,
            'company' => $company,
            'contact_email' => $email,
            'purchased_reports' => ''
        ));
        $account_created = $client_created && $this->db->insert('client_accounts', array(
            'client_id' => $client_id,
            'email' => $email,
            'password_hash' => $password_hash
        ));

        if (!$account_created || $this->db->trans_status() === FALSE || !$this->db->trans_commit()) {
            $this->db->trans_rollback();
            log_message('error', 'Client account registration transaction failed.');

            if ($this->find_by_email($email)) {
                return array('status' => 'duplicate');
            }

            return array('status' => 'error');
        }

        return array(
            'status' => 'created',
            'client_id' => $client_id,
            'company' => $company,
            'email' => $email
        );
    }
}

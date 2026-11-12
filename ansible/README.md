# Sanitized example: RHEL Chrony clients

This sample illustrates a **documented lab pattern** (Ansible-managed Linux time synchronization). It is **adapted**, not a raw export of the user's source reports. It is intentionally limited to RHEL-compatible clients; the macOS branch would require a separate workflow and privilege model.

Set `chrony_server` to a **trusted, reachable time source** before deployment. The placeholder is not an operational NTP endpoint. Run only after checking host inventory and change controls.

```bash
ansible-playbook -i <your-inventory> playbooks/chrony_client.yml --check --diff
ansible-playbook -i <your-inventory> playbooks/chrony_client.yml
```

Validation after deployment: `chronyc sources -v`, `timedatectl status`, and `systemctl status chronyd`.

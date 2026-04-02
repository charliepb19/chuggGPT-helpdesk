AUTOMATION_POLICIES = {
    "dns_flush": {
        "risk_level": "low",
        "requires_confirmation": False,
        "admin_only": False,
    },
    "network_reset": {
        "risk_level": "medium",
        "requires_confirmation": True,
        "admin_only": False,
    },
    "printer_restart": {
        "risk_level": "low",
        "requires_confirmation": False,
        "admin_only": False,
    },
    "disk_cleanup": {
        "risk_level": "low",
        "requires_confirmation": False,
        "admin_only": False,
    },
    "password_reset": {
        "risk_level": "high",
        "requires_confirmation": True,
        "admin_only": True,
    },
    "restart_service": {
        "risk_level": "medium",
        "requires_confirmation": True,
        "admin_only": True,
    },
}


def get_automation_policy(action_name: str) -> dict:
    default_policy = {
        "risk_level": "high",
        "requires_confirmation": True,
        "admin_only": True,
    }
    return AUTOMATION_POLICIES.get(action_name, default_policy)
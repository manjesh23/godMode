import os
import subprocess as sp
import base64
from flask import Flask, render_template, jsonify, send_from_directory
import psutil
from typing import Optional, Dict, Any
import logging
from jinja2 import Environment, FileSystemLoader

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
CONFIG = {
    'TEMPLATES_DIR': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
    'STATIC_DIR': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'),
    'LOG_FILE_PATH': '/var/log/ns.log',
    'LOGO_PATH': "/var/netscaler/gui/admin_ui/common/css/ns/ns_logo_with_name.svg",
    'PORT': 23000,
    'UPDATE_INTERVAL': 5000  # milliseconds
}

# Ensure the directories exist
os.makedirs(CONFIG['TEMPLATES_DIR'], exist_ok=True)
os.makedirs(CONFIG['STATIC_DIR'], exist_ok=True)

logger.debug(f"Templates directory: {CONFIG['TEMPLATES_DIR']}")
logger.debug(f"Template files: {os.listdir(CONFIG['TEMPLATES_DIR'])}")

def run_command(command: str) -> str:
    """Execute a shell command and return its output."""
    try:
        result = sp.run(command, shell=True, text=True, stdout=sp.PIPE, stderr=sp.PIPE, timeout=10)
        result.check_returncode()
        return result.stdout.strip()
    except sp.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        return f"Command failed: {e}"
    except sp.TimeoutExpired:
        logger.error(f"Command timed out: {command}")
        return "Command timed out"

def get_system_info() -> Dict[str, str]:
    """Get all system information in one call."""
    logger.debug("Getting system info...")
    info = {
        # Basic System Info
        'disk_usage': run_command("df -kh"),
        'nsppe_pid': run_command("nsp | awk '/started/||/NSPPE/'"),
        'systime': run_command("date"),
        'nsip': run_command("nscli -U %%:nsroot:. show ns ip | awk '/NetScaler/{print $2}'"),
        'hostname': run_command("nscli -U %%:nsroot:. show hostname | awk '/Hostname/{print $NF}'"),
        'nsversion': run_command("nscli -U %%:nsroot:. show ns version | awk '/Build/&&/NetScaler/{print $2, $4}' | sed 's/.$//'"),
        
        # Hardware Info
        'cpu_usage': run_command('nscli -U %%:nsroot:. shell "vmstat 1 1 | tail -1 | awk \'{print 100-$15}\'"'),
        'memory_usage': run_command('nscli -U %%:nsroot:. shell "free | grep Mem | awk \'{print $3/$2 * 100.0}\'"'),
        'disk_usage_detailed': run_command('nscli -U %%:nsroot:. shell "df -h"'),
        
        # Network Info
        'interfaces': run_command("nscli -U %%:nsroot:. show interface | awk '!/Done/'"),
        'vlan': run_command("nscli -U %%:nsroot:. show vlan | awk '!/Done/'"),
        'nsvlan': run_command("nscli -U %%:nsroot:. show nsvlan | awk '!/Done/'"),
        
        # Service Info
        'services': run_command("nscli -U %%:nsroot:. show service | awk '!/Done/'"),
        'servicegroups': run_command("nscli -U %%:nsroot:. show servicegroup | awk '!/Done/'"),
        
        # Load Balancing Info
        'lbvserver': run_command("nscli -U %%:nsroot:. stat lb vserver | awk '!/Done/'"),
        'csvserver': run_command("nscli -U %%:nsroot:. stat cs vserver | awk '!/Done/'"),
        'gslbvserver': run_command("nscli -U %%:nsroot:. stat gslb vserver | awk '!/Done/'"),
        
        # SSL Info
        'ssl_cert': run_command("nscli -U %%:nsroot:. show ssl certKey | awk '!/Done/'"),
        'ssl_stats': run_command("nscli -U %%:nsroot:. stat ssl | awk '!/Done/'"),
        
        # System Stats
        'system_stats': run_command("nscli -U %%:nsroot:. stat system | awk '!/Done/'"),
        'ha_status': run_command("nscli -U %%:nsroot:. show ha node | awk '!/Done/'"),
        
        # License Info
        'license': run_command("nscli -U %%:nsroot:. show license | awk '!/Done/'"),
        
        # Feature Status
        'features': run_command("nscli -U %%:nsroot:. show feature | awk '!/Done/'"),
        
        # Configuration
        'config': run_command("nscli -U %%:nsroot:. show running config | awk '!/Done/'")
    }
    logger.debug(f"System info retrieved: {info}")
    return info

def get_logs(log_type: str) -> str:
    """Get filtered logs based on type (CLI or GUI)."""
    if not os.path.exists(CONFIG['LOG_FILE_PATH']):
        logger.error(f"Log file not found: {CONFIG['LOG_FILE_PATH']}")
        return f"{log_type} log file not found."
    
    try:
        with open(CONFIG['LOG_FILE_PATH'], 'r') as f:
            lines = f.readlines()[-50:]
            filter_pattern = 'CLI CMD_EXECUTED' if log_type == 'CLI' else 'GUI CMD_EXECUTED'
            filtered_lines = [line for line in lines if filter_pattern in line]
            return ''.join(filtered_lines)
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return f"Error reading {log_type} logs"

def get_logo_base64() -> str:
    """Get the logo as base64 encoded string."""
    try:
        with open(CONFIG['LOGO_PATH'], 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Error reading logo: {e}")
        return ""

# Routes
@app.route('/')
def index():
    logger.debug("Index route accessed")
    try:
        system_info = get_system_info()
        logger.debug("System info retrieved successfully")
        logo_base64 = get_logo_base64()
        logger.debug("Logo retrieved successfully")
        return render_template('index.html',
                             system_info=system_info,
                             logo_base64=logo_base64,
                             update_interval=CONFIG['UPDATE_INTERVAL'])
    except Exception as e:
        logger.error(f"Error in index route: {e}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/system-info')
def system_info():
    logger.debug("System info route accessed")
    return jsonify(get_system_info())

@app.route('/logs/<log_type>')
def logs(log_type):
    logger.debug(f"Logs route accessed for type: {log_type}")
    if log_type not in ['CLI', 'GUI']:
        return "Invalid log type", 400
    return get_logs(log_type)

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    # Run the Flask app
    app.run(host='0.0.0.0', port=CONFIG['PORT'], debug=True)

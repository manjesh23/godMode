import os
import subprocess as sp
import base64
from flask import Flask, render_template, jsonify
import psutil

app = Flask(__name__)

# Define the directory where templates are stored
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

# Ensure the templates directory exists
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)

# Path to the index.html file
index_file_path = os.path.join(templates_dir, 'index.html')

# Define the ns.log file path
log_file_path = '/var/log/ns.log'

def run_command(command):
    try:
        result = sp.run(command, shell=True, text=True, stdout=sp.PIPE, stderr=sp.PIPE)
        result.check_returncode()  # This will raise an error if the command failed
        return result.stdout.strip()
    except sp.CalledProcessError as e:
        return f"Command failed: {e}"

def get_disk_usage():
    return run_command("df -kh")

def get_NSPPE_PID():
    return run_command("nsp | awk '/started/||/NSPPE/'")

def get_systime():
    return run_command("date")

def get_lbvserver():
    return run_command("nscli -U %%:nsroot:. stat lb vserver | awk '!/Done/'")

# Get NSIP and Hostname
nsip = run_command("nscli -U %%:nsroot:. show ns ip | awk '/NetScaler/{print $2}'")
hostname = run_command("nscli -U %%:nsroot:. show hostname | awk '/Hostname/{print $NF}'")
nsvserion = run_command("nscli -U %%:nsroot:. show ns version | awk '/Build/&&/NetScaler/{print $2, $4}' | sed 's/.$//'")

# Path to the SVG image file
logo = "/var/netscaler/gui/admin_ui/common/css/ns/ns_logo_with_name.svg"

# Read the SVG image content and encode it in base64
with open(logo, 'rb') as f:
    svg_image_content = base64.b64encode(f.read()).decode('utf-8')

# CSS styles
css_styles = """
<style>
    body {
        background-color: black;
        color: white;
    }
    h1 img {
        display: block;
        margin: 0 auto;
    }
    hr {
        height: 2px;
        background-color: white;
        border: none;
    }
    pre {
        background-color: black;
        color: white;
        padding: 10px;
        overflow: auto;
        white-space: pre-wrap;
    }
    .tab {
        overflow: hidden;
        border: 1px solid #ccc;
        background-color: #f1f1f1;
    }
    .tab button {
        background-color: inherit;
        float: left;
        border: none;
        outline: none;
        cursor: pointer;
        padding: 14px 16px;
        transition: 0.3s;
    }
    .tab button:hover {
        background-color: #ddd;
    }
    .tab button.active {
        background-color: #ccc;
    }
    .tabcontent {
        display: none;
        padding: 6px 12px;
        border: 1px solid #ccc;
        border-top: none;
    }
</style>
"""

# HTML content
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{hostname} godMode</title>
    {css_styles}
    <script>
        function openTab(evt, tabName) {{
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tabcontent");
            for (i = 0; i < tabcontent.length; i++) {{
                tabcontent[i].style.display = "none";
            }}
            tablinks = document.getElementsByClassName("tablinks");
            for (i = 0; i < tablinks.length; i++) {{
                tablinks[i].className = tablinks[i].className.replace(" active", "");
            }}
            document.getElementById(tabName).style.display = "block";
            evt.currentTarget.className += " active";
        }}

        // Function to update disk usage
        function updateDiskUsage() {{
            fetch('/disk-usage')
                .then(response => response.text())
                .then(data => {{
                    document.getElementById('disk-usage').innerText = data;
                }});
        }}

        // Function to update NSPPE PID
        function updateNSPPEPID() {{
            fetch('/nsppe-pid')
                .then(response => response.text())
                .then(data => {{
                    document.getElementById('nsppe-pid').innerText = data;
                }});
        }}

        // Function to update system time
        function updateSysTime() {{
            fetch('/systime')
                .then(response => response.text())
                .then(data => {{
                    document.getElementById('systime').innerText = data;
                }});
        }}

        // Function to update CLI and GUI logs
        function updateLogs() {{
            fetch('/clilogs')
                .then(response => response.text())
                .then(data => {{
                    document.getElementById('cli-log-output').innerText += data;
                    var cliLogDiv = document.getElementById('cli-log-output');
                    cliLogDiv.scrollTop = cliLogDiv.scrollHeight;
                }});
            fetch('/guilogs')
                .then(response => response.text())
                .then(data => {{
                    document.getElementById('gui-log-output').innerText += data;
                    var guiLogDiv = document.getElementById('gui-log-output');
                    guiLogDiv.scrollTop = guiLogDiv.scrollHeight;
                }});
        }}

        // Function to update lb vserver
        function updatelbvserver() {{
            fetch('/lbvserver')
                .then(response => response.text())
                .then(data => {{
                    document.getElementById('lbvserver').innerText = data;
                }});
        }}

        // Initial calls to update data
        updateDiskUsage();
        updateNSPPEPID();
        updateSysTime();
        updateLogs();
        updatelbvserver();

        // Set intervals to update data every 5 seconds
        setInterval(updateDiskUsage, 5000);
        setInterval(updateNSPPEPID, 5000);
        setInterval(updateSysTime, 5000);
        setInterval(updateLogs, 5000);
        setInterval(updatelbvserver, 5000);
    </script>
</head>
<body>
    <h1><img src="data:image/svg+xml;base64,{svg_image_content}" alt="{hostname} Logo"></h1>
    <div class="tab">
        <button class="tablinks" onclick="openTab(event, 'SystemInfo')">System Info</button>
        <button class="tablinks" onclick="openTab(event, 'Logs')">CLI and GUI Logs</button>
        <button class="tablinks" onclick="openTab(event, 'vServer')">vServer Details</button>
    </div>
    <div id="SystemInfo" class="tabcontent">
        <p>NetScaler NSIP: {nsvserion}</p>
        <p>NetScaler Time: <span id="systime">{get_systime()}</span></p>
        <p>NetScaler NSIP: {nsip}</p>
        <p>NetScaler Hostname: {hostname}</p>
        <hr>
        <p>NSPPE PID:</p>
        <pre id="nsppe-pid">{get_NSPPE_PID()}</pre>
        <hr>
        <p>Disk Usage:</p>
        <pre id="disk-usage">{get_disk_usage()}</pre>
    </div>
    <div id="Logs" class="tabcontent">
        <p>Real-Time CLI Command Output:</p>
        <pre id="cli-log-output" style="height: 450px; overflow-y: scroll;"></pre>
        <p>Real-Time GUI Command Output:</p>
        <pre id="gui-log-output" style="height: 450px; overflow-y: scroll;"></pre>
    </div>
    <div id="vServer" class="tabcontent">
    <div>LB vServer</div>
    <pre id="lbvserver"></pre>
    <script>
        document.getElementsByClassName('tablinks')[0].click();
    </script>
</body>
</html>"""

# Write the HTML content to index.html
with open(index_file_path, 'w') as f:
    f.write(html_content)

@app.route('/')
def hello():
    return render_template('index.html')

@app.route('/disk-usage')
def disk_usage():
    return get_disk_usage()

@app.route('/nsppe-pid')
def nsppe_pid():
    return get_NSPPE_PID()

@app.route('/systime')
def systime():
    return get_systime()

@app.route('/clilogs')
def clilogs():
    if os.path.exists(log_file_path):
        with open(log_file_path, 'r') as f:
            lines = f.readlines()[-50:]
            filtered_lines = [line for line in lines if 'CLI CMD_EXECUTED' in line]
            return ''.join(filtered_lines)
    return "CLI log file not found."

@app.route('/guilogs')
def guilogs():
    if os.path.exists(log_file_path):
        with open(log_file_path, 'r') as f:
            lines = f.readlines()[-50:]
            filtered_lines = [line for line in lines if 'GUI CMD_EXECUTED' in line]
            return ''.join(filtered_lines)
    return "GUI log file not found."

@app.route('/lbvserver')
def lbvserver():
    return get_lbvserver()

if __name__ == '__main__':
    app.run(host=nsip, port=23000, debug=True)

import os
import subprocess as sp
import base64
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# Define the directory where templates are stored
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

# Ensure the templates directory exists
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)

# Path to the index.html file
index_file_path = os.path.join(templates_dir, 'index.html')

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

# Get NSIP and Hostname
nsip = run_command("nscli -U %%:nsroot:. show ns ip | awk '/NetScaler/{print $2}'")
hostname = run_command("nscli -U %%:nsroot:. show hostname | awk '/Hostname/{print $NF}'")

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

        // Initial calls to update data
        updateDiskUsage();
        updateNSPPEPID();
        updateSysTime();

        // Set intervals to update data every 5 seconds
        setInterval(updateDiskUsage, 5000);
        setInterval(updateNSPPEPID, 5000);
        setInterval(updateSysTime, 5000);
    </script>
</head>
<body>
    <h1><img src="data:image/svg+xml;base64,{svg_image_content}" alt="{hostname} Logo"></h1>
    <p>NetScaler Time: <span id="systime">{get_systime()}</span></p>
    <p>NetScaler NSIP: {nsip}</p>
    <p>NetScaler Hostname: {hostname}</p>
    <br>
    <p>NSPPE PID:</p>
    <pre id="nsppe-pid">{get_NSPPE_PID()}</pre>
    <p>Disk Usage:</p>
    <pre id="disk-usage">{get_disk_usage()}</pre>
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

if __name__ == '__main__':
    app.run(host=nsip, port=23000, debug=True)

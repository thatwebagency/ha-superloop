<div class="_main_5jn6z_1 z-10 markdown prose dark:prose-invert contain-inline-size focus:outline-hidden bg-transparent ProseMirror" contenteditable="true" style="width: 775px;" translate="no">
<h1>🏄‍♂️ Superloop Home Assistant Integration</h1>
<p>A sleek Home Assistant integration to monitor your <strong>Superloop</strong> broadband usage, plan, and billing status. Now with <strong>Usage Alerts</strong> and beautiful <strong>Mini Graph Cards</strong> support!</p>

<hr>

<h2>🌟 Features</h2>
<p>This integration provides real-time Superloop account sensors for:</p>
<ul>
  <li>📈 <strong>Data Usage</strong> (Free Download / Upload)</li>
  <li>🚀 <strong>Download Speed</strong> (Evening Plan Speed)</li>
  <li>🗕️ <strong>Billing Cycle Progress</strong></li>
  <li>📃 <strong>Plan Name</strong></li>
  <li>📦 <strong>Plan Allowance</strong> (e.g., "Unlimited Data" or "500 GB")</li>
  <li>🗓️ <strong>Billing Cycle Dates</strong></li>
  <li>⚡ <strong>Automatic Refreshing</strong> and <strong>Silent Re-Authentication</strong></li>
</ul>

<hr>

<h2>🚀 Installation</h2>

<h3>HACS Installation (Recommended)</h3>
<ol>
  <li>Open HACS in Home Assistant</li>
  <li>Navigate to <strong>Integrations</strong></li>
  <li>Click the three dots (...) → <strong>Custom Repositories</strong></li>
  <li>Add <strong>this GitHub repo URL</strong> as a <strong>"Integration"</strong> type</li>
  <li>Click <strong>Add</strong></li>
  <li>Search for <strong>Superloop</strong> under Integrations</li>
  <li>Click <strong>Install</strong></li>
  <li>Restart Home Assistant</li>
</ol>

<h3>Manual Installation</h3>
<ol>
  <li>Copy the <code>custom_components/superloop</code> folder into your Home Assistant <code>custom_components/</code> directory.</li>
  <li>Restart Home Assistant.</li>
</ol>

<hr>

<h2>⚙️ Configuration</h2>
<ol>
  <li>Go to <strong>Settings → Devices &amp; Services</strong></li>
  <li>Click <strong>+ Add Integration</strong></li>
  <li>Search for <strong>Superloop</strong></li>
  <li>Enter your <strong>Superloop email</strong> and <strong>password</strong> to link your account.</li>
</ol>
<p>Done! Your sensors will now appear automatically.</p>

<hr>

<h2>📈 Dashboard Setup</h2>
<p>We recommend installing the <strong>mini-graph-card</strong> from HACS to beautifully display your Superloop data.</p>
<p>Example dashboard card:</p>

<pre>
<code>
type: custom:mini-graph-card
name: Download Usage
icon: mdi:download
entities:
  - entity: sensor.superloop_free_download_usage
show:
  name: true
  icon: true
  state: true
  graph: line
  labels: false
line_width: 5
font_size: 80
smoothing: true
height: 150
style: |
  ha-card {
    background: rgba(20, 20, 20, 0.9);
    border-radius: 16px;
  }
</code>
<code>
type: custom:mini-graph-card
name: Upload Usage
icon: mdi:upload
entities:
  - entity: sensor.superloop_free_upload_usage
show:
  name: true
  icon: true
  state: true
  graph: line
  labels: false
line_width: 5
font_size: 80
smoothing: true
height: 150
style: |
  ha-card {
    background: rgba(20, 20, 20, 0.9);
    border-radius: 16px;
  }
</code>
</pre>

<p>🔵 This will show your <strong>last 30 days</strong> of free download and upload usage visually!</p>

<hr>

<h2>📢 Usage Alerts via Blueprint (New!)</h2>
<p>Want to be notified when your usage hits <strong>90% of your Plan Allowance</strong>?</p>
<p>We built a ready-to-go automation for you! 🎯</p>

<ul>
  <li>Monitors your <strong>Data Usage</strong> vs your <strong>Plan Allowance</strong>.</li>
  <li>Automatically <strong>skips alerts for Unlimited plans</strong>.</li>
  <li>Sends a <strong>persistent notification</strong> if you cross 90%!</li>
</ul>

<p>🎯 <strong>No YAML editing needed</strong> — just pick your usage sensor and plan allowance sensor when setting it up!</p>

<p>👉 <a href="https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fthatwebagency%2Fha-superloop%2Fblob%2Fmaster%2Fblueprints%2Fautomation%2Fthatwebagency%2Fsuperloop_usage_alert.yaml" target="_blank" rel="noreferrer noopener"><img src="https://my.home-assistant.io/badges/blueprint_import.svg" alt="Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled." /></a></p>

<hr>

<h2>📅 Daily Usage Tracking (Optional)</h2>

<p>Track your <strong>daily Superloop download and upload usage</strong> automatically!</p>

<h3>Step 1: Create Helpers</h3>
<p>Create 4 <strong>Input Number</strong> helpers:</p>
<ul>
  <li>Superloop Free Download Yesterday</li>
  <li>Superloop Non-Free Download Yesterday</li>
  <li>Superloop Free Upload Yesterday</li>
  <li>Superloop Non-Free Upload Yesterday</li>
</ul>
<p>Settings: Minimum: 0, Maximum: 100000, Unit: GB, Step: 0.1</p>

<h3>Step 2: Save Yesterday's Usage (Automation)</h3>
<p>👉 <a href="https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fthatwebagency%2Fha-superloop%2Fblob%2Fmaster%2Fblueprints%2Fautomation%2Fthatwebagency%2Fsave_superloop_yesterday.yaml" target="_blank" rel="noreferrer noopener"><img src="https://my.home-assistant.io/badges/blueprint_import.svg" alt="Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled." /></a></p>

<h3>Step 3: Create Daily Usage Sensors</h3>
<p>👉 <a href="https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fthatwebagency%2Fha-superloop%2Fblob%2Fmaster%2Fblueprints%2Ftemplate%2Fthatwebagency%2Fdaily_superloop_usage.yaml" target="_blank" rel="noreferrer noopener"><img src="https://my.home-assistant.io/badges/blueprint_import.svg" alt="Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled." /></a></p>

<h3>Step 4: Add to your Dashboard</h3>

<pre>
<code>
type: custom:mini-graph-card
name: Superloop Daily Usage
hours_to_show: 720
points_per_hour: 1
entities:
  - entity: sensor.superloop_daily_free_download_usage
  - entity: sensor.superloop_daily_nonfree_download_usage
  - entity: sensor.superloop_daily_free_upload_usage
  - entity: sensor.superloop_daily_nonfree_upload_usage
</code>
</pre>

<p>🎯 Done! You now have beautiful per-day tracking graphs!</p>

<hr>

<h2>🛠️ Troubleshooting</h2>
<ul>
  <li>Check Home Assistant <strong>Logs</strong> if sensors are missing.</li>
  <li>Verify your <strong>Superloop credentials</strong> are correct.</li>
  <li>If the billing cycle does not reset properly, verify <strong>API access</strong>.</li>
  <li>Open an <a href="https://github.com/thatwebagency/ha-superloop/issues">issue on GitHub</a> if stuck.</li>
</ul>

<hr>

<h2>❤️ Support</h2>
<p>If you find this integration useful, please ⭐️ star the repository! Need help? Open a <a href="https://github.com/thatwebagency/ha-superloop/issues">GitHub Issue</a>.</p>

<hr>

<p>🏄‍♂️ Surf your data usage. Stay in control. Built with love for the Home Assistant community. 🏡</p>
</div>

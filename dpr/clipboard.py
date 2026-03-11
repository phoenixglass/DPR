"""
Browser clipboard helpers for Streamlit.

Provides a JS-based one-click copy button that uses navigator.clipboard.writeText().
Falls back to document.execCommand('copy') for older browsers.
"""

from __future__ import annotations

import html as _html
import hashlib


def _escape_js_string(text: str) -> str:
    """
    Escape text so it can be safely embedded in a JS template-literal (backtick string).
    Escapes backticks, backslashes, and dollar signs used in template literals.
    """
    text = text.replace("\\", "\\\\")
    text = text.replace("`", "\\`")
    text = text.replace("$", "\\$")
    return text


def copy_button_html(text: str, button_label: str, key: str = "") -> str:
    """
    Return an HTML snippet that renders a button.
    Clicking it copies ``text`` to the clipboard via navigator.clipboard.writeText().

    Parameters
    ----------
    text : str
        The text to copy.
    button_label : str
        Label shown on the button.
    key : str
        Optional unique key to disambiguate multiple buttons on the same page.
    """
    safe_text = _escape_js_string(text)
    btn_id = "cpbtn_" + hashlib.md5((button_label + key).encode()).hexdigest()[:8]
    safe_label = _html.escape(button_label)

    return f"""
<button
  id="{btn_id}"
  onclick="(function(){{
    var txt = `{safe_text}`;
    if (navigator.clipboard && navigator.clipboard.writeText) {{
      navigator.clipboard.writeText(txt).then(
        function() {{
          var btn = document.getElementById('{btn_id}');
          var orig = btn.textContent;
          btn.textContent = 'Copied!';
          setTimeout(function(){{ btn.textContent = orig; }}, 1500);
        }},
        function(err) {{ console.error('Clipboard write failed', err); }}
      );
    }} else {{
      var ta = document.createElement('textarea');
      ta.value = txt;
      ta.style.position = 'fixed';
      ta.style.top = '0';
      ta.style.left = '0';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      try {{ document.execCommand('copy'); }} catch(e) {{}}
      document.body.removeChild(ta);
      var btn = document.getElementById('{btn_id}');
      var orig = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(function(){{ btn.textContent = orig; }}, 1500);
    }}
  }})()">
  {safe_label}
</button>
"""

# Logs and dismisses modal message boxes that PDM itself raises while the harness drives its price update.
# PDM reports failures with Interaction.MsgBox (title "PDMMaintenance"); an interactive user clicks OK, so the
# watcher records the exact dialog text (that text IS PDM behaviour worth reporting) and closes it (WM_CLOSE),
# which is equivalent to OK for an OK-only box. Any other dialog is logged the same way.
param(
    [Parameter(Mandatory = $true)][string]$LogPath,
    [int]$Seconds = 1800,
    [string]$Title = "PDMMaintenance"
)
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices;
public class PdmDialogs {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc p, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr p, EnumProc cb, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  public static string[] CloseAll(string title) {
    var found = new System.Collections.Generic.List<string>();
    EnumWindows((h, l) => {
      var t = new StringBuilder(512); GetWindowText(h, t, 512);
      var c = new StringBuilder(64); GetClassName(h, c, 64);
      if (t.ToString() != title || c.ToString() != "#32770" || !IsWindowVisible(h)) return true;
      var body = new StringBuilder();
      EnumChildWindows(h, (ch, l2) => { var tx = new StringBuilder(8192); GetWindowText(ch, tx, 8192);
        var cl = new StringBuilder(64); GetClassName(ch, cl, 64);
        if (cl.ToString() == "Static" && tx.Length > 0) body.AppendLine(tx.ToString()); return true; }, IntPtr.Zero);
      found.Add(body.ToString());
      SendMessage(h, 0x0010, IntPtr.Zero, IntPtr.Zero);
      return true; }, IntPtr.Zero);
    return found.ToArray();
  }
}
"@
$end = (Get-Date).AddSeconds($Seconds)
while ((Get-Date) -lt $end) {
    foreach ($text in [PdmDialogs]::CloseAll($Title)) {
        $entry = [ordered]@{ time = (Get-Date).ToString("o"); dialog = $text.Trim() }
        Add-Content -LiteralPath $LogPath -Value ($entry | ConvertTo-Json -Compress) -Encoding UTF8
    }
    Start-Sleep -Milliseconds 700
}

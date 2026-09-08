using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Windows.Forms;

internal static class Launcher
{
    private delegate bool EnumWindowsProc(IntPtr window, IntPtr parameter);
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumWindowsProc callback, IntPtr parameter);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr window);
    [DllImport("user32.dll")] private static extern bool IsIconic(IntPtr window);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int GetWindowText(IntPtr window, StringBuilder text, int count);
    [DllImport("user32.dll")] private static extern bool ShowWindowAsync(IntPtr window, int command);
    [DllImport("user32.dll")] private static extern bool SetForegroundWindow(IntPtr window);
    private const int Restore = 9;

    private static bool ActivateExistingWindow()
    {
        IntPtr match = IntPtr.Zero;
        EnumWindows(delegate(IntPtr window, IntPtr parameter) {
            if (!IsWindowVisible(window)) return true;
            var title = new StringBuilder(256);
            GetWindowText(window, title, title.Capacity);
            if (title.ToString() != "MENTAT") return true;
            match = window;
            return false;
        }, IntPtr.Zero);
        if (match == IntPtr.Zero) return false;
        if (IsIconic(match)) ShowWindowAsync(match, Restore);
        SetForegroundWindow(match);
        return true;
    }

    [STAThread]
    private static int Main()
    {
        string errorLog = Path.Combine(Path.GetTempPath(), "MENTAT-launch-" + Guid.NewGuid().ToString("N") + ".log");
        try
        {
            if (ActivateExistingWindow()) return 0;
            string script = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "Start-MentatApp.ps1"));
            if (!File.Exists(script)) throw new FileNotFoundException("The MENTAT application folder is missing. Run Install MENTAT again.");
            var start = new ProcessStartInfo("powershell.exe", "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"" + script + "\" -AppWindow -ErrorLog \"" + errorLog + "\"") {
                UseShellExecute = false, CreateNoWindow = true
            };
            using (var process = Process.Start(start))
            {
                process.WaitForExit();
                if (process.ExitCode != 0) throw new Exception(File.Exists(errorLog) ? File.ReadAllText(errorLog).Trim() : "Check the local startup logs for details.");
            }
            for (int attempt = 0; attempt < 40; attempt++)
            {
                if (ActivateExistingWindow()) break;
                Thread.Sleep(250);
            }
            return 0;
        }
        catch (Exception error)
        {
            MessageBox.Show("MENTAT could not open.\n\n" + error.Message +
                "\n\nStartup logs: " + Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Mentat", "console"),
                "MENTAT", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
        finally { if (File.Exists(errorLog)) File.Delete(errorLog); }
    }
}

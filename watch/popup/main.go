// Command watch-popup opens the live-triage board as a panvim view. Replaces
// the bash script of the same name; the panvim invocation is unchanged, so
// panel/keys.tsv and panel/syntax.tsv (which reference {ctl} and {log})
// needed no edits.
//
// syscall.Exec, not exec.Command: the bash version ended in `exec panvim
// ...`, replacing the shell process rather than spawning a child under it,
// so panvim owns the terminal directly (signals, resize, Ctrl-C all go
// straight to it, with nothing sitting in between to get that wrong).
package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
)

func main() {
	here, err := findWatchDir()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	panvim, err := exec.LookPath("panvim")
	if err != nil {
		fmt.Fprintln(os.Stderr, "panvim not on PATH")
		os.Exit(1)
	}
	ctl := filepath.Join(here, "watch-ctl")
	if _, err := os.Stat(ctl); err != nil {
		fmt.Fprintf(os.Stderr, "watch-ctl not built yet -- see %s/README.md\n", here)
		os.Exit(1)
	}

	args := []string{
		"panvim", "view",
		"--title", "sdoc-watch",
		"--render", fmt.Sprintf(`%s board > "$PANVIM_OUT" 2>&1`, ctl),
		"--interval", "3",
		"--keys", filepath.Join(here, "panel", "keys.tsv"),
		"--syntax", filepath.Join(here, "panel", "syntax.tsv"),
		// Deliberately unanchored: matches the id wherever one appears on
		// the cursor line -- a flagged card's ">> email_NNN" header AND a
		// plain history-table row, which is the only place a corrected
		// email still shows once it resolves to OK and drops out of the
		// flagged section. [%w%-]+ (not just digits) also covers resend.py's
		// own "email_004-fix153000" ids. False-positive risk is low and
		// harmless: the only other line containing "email_" is the table's
		// own header ("email_id"), which resend.py/delete_email.py just
		// reject as "no such email" if a key is pressed on it.
		"--row", `(email_[%w%-]+)`,
		"--state", filepath.Join(here, "state"),
		"--var", "ctl=" + ctl,
		"--var", "log=" + filepath.Join(here, "state", "daemon.log"),
		"--var", "ailog=" + filepath.Join(here, "state", "ai_fix.log"),
	}
	if err := syscall.Exec(panvim, args, os.Environ()); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

// findWatchDir walks up from the binary's own location looking for the
// directory that contains panel/keys.tsv -- watch/. Same reasoning as
// watch-ctl's own search: a hardcoded depth broke the moment that binary's
// build output moved, so this one never assumes a fixed layout either.
func findWatchDir() (string, error) {
	exe, err := os.Executable()
	if err != nil {
		return "", err
	}
	dir := filepath.Dir(exe)
	for i := 0; i < 6; i++ {
		if _, err := os.Stat(filepath.Join(dir, "panel", "keys.tsv")); err == nil {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	// `go run .` etc: fall back to the working directory.
	wd, err := os.Getwd()
	if err != nil {
		return "", err
	}
	dir = wd
	for i := 0; i < 6; i++ {
		if _, err := os.Stat(filepath.Join(dir, "panel", "keys.tsv")); err == nil {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return "", fmt.Errorf("could not find watch/ (panel/keys.tsv) above %s or %s", filepath.Dir(exe), wd)
}

// Command watch-ctl controls the SDOC live-triage daemon (../daemon.py).
// Same command surface as pr-watch-ctl and the bash script this replaces:
// start/stop/restart/status/board/log/feed/reset. This binary owns process
// lifecycle and the state files only -- classification stays in Python
// because daemon.py imports dock, the graded package; nothing here
// reimplements or touches that logic.
package main

import (
	"bufio"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"
)

// here is the watch/ directory: this binary's own parent, resolved once so
// it works regardless of the caller's cwd -- the bash version relied on
// BASH_SOURCE for the same reason.
var here string

func main() {
	exe, err := os.Executable()
	must(err)
	found, err := findWatchDir(filepath.Dir(exe))
	if err != nil {
		// `go run .` etc: fall back to searching from the working directory.
		found, err = findWatchDir(mustGetwd())
		must(err)
	}
	here = found

	if len(os.Args) < 2 {
		usage()
		os.Exit(1)
	}
	cmd := os.Args[1]
	args := os.Args[2:]

	var runErr error
	switch cmd {
	case "start":
		runErr = start()
	case "stop":
		runErr = stop()
	case "restart":
		if err := stop(); err != nil {
			runErr = err
			break
		}
		runErr = start()
	case "status":
		runErr = status()
	case "board":
		runErr = board()
	case "log":
		runErr = tailLog()
	case "feed":
		runErr = feed(args)
	case "reset":
		runErr = reset()
	default:
		usage()
		os.Exit(1)
	}
	if runErr != nil {
		fmt.Fprintln(os.Stderr, runErr)
		os.Exit(1)
	}
}

func usage() {
	fmt.Fprintln(os.Stderr, "usage: watch-ctl {start|stop|restart|status|board|log|feed [n] [--rate s] [--shuffle]|reset}")
}

// findWatchDir walks up from start looking for a directory that contains
// daemon.py -- watch/. The binary's exact placement (watch/, watch/ctl/,
// wherever a build puts it) does not have to be hardcoded to find it; a
// fixed depth assumption was the first cut's bug, caught by the first real
// `start` after moving the build output.
func findWatchDir(start string) (string, error) {
	dir := start
	for i := 0; i < 6; i++ {
		if _, err := os.Stat(filepath.Join(dir, "daemon.py")); err == nil {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return "", fmt.Errorf("could not find watch/ (daemon.py) above %s", start)
}

func mustGetwd() string {
	wd, err := os.Getwd()
	must(err)
	return wd
}

func must(err error) {
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func stateDir() string  { return filepath.Join(here, "state") }
func pidFile() string   { return filepath.Join(stateDir(), "daemon.pid") }
func logFile() string   { return filepath.Join(stateDir(), "daemon.log") }
func boardFile() string { return filepath.Join(stateDir(), "board.txt") }
func eventsFile() string {
	return filepath.Join(stateDir(), "events.jsonl")
}

func pythonBin() string {
	if p := os.Getenv("PYTHON"); p != "" {
		return p
	}
	return "python3"
}

// runningPID returns the daemon's pid if the pidfile names a live process,
// else 0. Matches the bash version's `kill -0` check.
func runningPID() int {
	b, err := os.ReadFile(pidFile())
	if err != nil {
		return 0
	}
	pid, err := strconv.Atoi(strings.TrimSpace(string(b)))
	if err != nil || pid <= 0 {
		return 0
	}
	proc, err := os.FindProcess(pid)
	if err != nil {
		return 0
	}
	if err := proc.Signal(syscall.Signal(0)); err != nil {
		return 0
	}
	return pid
}

// staleCode reports whether the running daemon predates the last edit to
// daemon.py. The pidfile's mtime is the daemon's start time (daemon.py
// writes it once, at startup), which beats parsing `ps -o lstart`.
//
// This exists because `start` is a no-op on an already-running daemon: edit
// daemon.py, run start, and you are silently still on the old code. That
// cost a real debugging cycle -- a board fix looked broken for several
// minutes because the process under test predated the fix by 86 seconds.
func staleCode() (time.Duration, bool) {
	pidInfo, err := os.Stat(pidFile())
	if err != nil {
		return 0, false
	}
	srcInfo, err := os.Stat(filepath.Join(here, "daemon.py"))
	if err != nil {
		return 0, false
	}
	if srcInfo.ModTime().After(pidInfo.ModTime()) {
		return srcInfo.ModTime().Sub(pidInfo.ModTime()), true
	}
	return 0, false
}

func warnIfStale() {
	if age, stale := staleCode(); stale {
		fmt.Fprintf(os.Stderr,
			"warning: daemon.py was edited %s after this daemon started -- it is running the OLD code.\n"+
				"         `watch-ctl restart` to pick the change up (`start` alone will not).\n",
			age.Round(time.Second))
	}
}

func start() error {
	if err := os.MkdirAll(stateDir(), 0o755); err != nil {
		return err
	}
	if pid := runningPID(); pid != 0 {
		fmt.Printf("already running (pid %d)\n", pid)
		warnIfStale()
		return nil
	}
	lf, err := os.OpenFile(logFile(), os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	defer lf.Close()

	c := exec.Command(pythonBin(), filepath.Join(here, "daemon.py"))
	c.Stdout = lf
	c.Stderr = lf
	c.SysProcAttr = &syscall.SysProcAttr{Setsid: true} // detach, survive this process exiting
	if err := c.Start(); err != nil {
		return fmt.Errorf("failed to start: %w", err)
	}
	// daemon.py writes its own pidfile once it's actually running; give it a
	// moment rather than trusting c.Process.Pid, which is this process's
	// immediate child and would be wrong if Python ever re-execs itself.
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		if runningPID() != 0 {
			fmt.Printf("started (pid %d)\n", runningPID())
			return nil
		}
		time.Sleep(50 * time.Millisecond)
	}
	return fmt.Errorf("failed to start -- see %s", logFile())
}

func stop() error {
	pid := runningPID()
	if pid == 0 {
		fmt.Println("not running")
		return nil
	}
	proc, err := os.FindProcess(pid)
	if err != nil {
		return err
	}
	_ = proc.Signal(syscall.SIGTERM)
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		if runningPID() == 0 {
			break
		}
		time.Sleep(100 * time.Millisecond)
	}
	if runningPID() != 0 {
		_ = proc.Signal(syscall.SIGKILL)
	}
	_ = os.Remove(pidFile())
	fmt.Println("stopped")
	return nil
}

func status() error {
	n := countLines(eventsFile())
	if pid := runningPID(); pid != 0 {
		fmt.Printf("running (pid %d) -- %d email(s) triaged\n", pid, n)
		warnIfStale()
	} else {
		fmt.Printf("stopped -- %d email(s) triaged\n", n)
	}
	return nil
}

func countLines(path string) int {
	f, err := os.Open(path)
	if err != nil {
		return 0
	}
	defer f.Close()
	n := 0
	sc := bufio.NewScanner(f)
	buf := make([]byte, 0, 64*1024)
	sc.Buffer(buf, 1024*1024)
	for sc.Scan() {
		if strings.TrimSpace(sc.Text()) != "" {
			n++
		}
	}
	return n
}

func board() error {
	b, err := os.ReadFile(boardFile())
	if errors.Is(err, os.ErrNotExist) {
		fmt.Println("# no board yet -- start the daemon and feed it")
		return nil
	}
	if err != nil {
		return err
	}
	fmt.Print(string(b))
	return nil
}

// tailLog follows daemon.log the way `tail -f` does: print what is there,
// then poll for growth. No external dependency, no cgo.
func tailLog() error {
	if _, err := os.Stat(logFile()); errors.Is(err, os.ErrNotExist) {
		if f, err := os.Create(logFile()); err == nil {
			f.Close()
		}
	}
	f, err := os.Open(logFile())
	if err != nil {
		return err
	}
	defer f.Close()
	// Seed with the last ~60 lines, same as `tail -n 60 -f`.
	all, _ := os.ReadFile(logFile())
	lines := strings.Split(strings.TrimRight(string(all), "\n"), "\n")
	if len(lines) > 60 {
		lines = lines[len(lines)-60:]
	}
	for _, l := range lines {
		if l != "" {
			fmt.Println(l)
		}
	}
	pos, _ := f.Seek(0, os.SEEK_END)
	for {
		time.Sleep(300 * time.Millisecond)
		info, err := os.Stat(logFile())
		if err != nil {
			continue
		}
		if info.Size() < pos {
			pos = 0 // log was rotated/reset
		}
		if info.Size() > pos {
			if _, err := f.Seek(pos, os.SEEK_SET); err != nil {
				continue
			}
			sc := bufio.NewScanner(f)
			for sc.Scan() {
				fmt.Println(sc.Text())
			}
			pos, _ = f.Seek(0, os.SEEK_CUR)
		}
	}
}

func feed(args []string) error {
	feeder := []string{filepath.Join(here, "feeder.py")}
	feeder = append(feeder, args...)
	c := exec.Command(pythonBin(), feeder...)
	c.Stdout = os.Stdout
	c.Stderr = os.Stderr
	return c.Run()
}

func reset() error {
	_ = stop()
	patterns := []string{
		filepath.Join(stateDir(), "*.jsonl"),
		filepath.Join(stateDir(), "*.log"),
		filepath.Join(stateDir(), "board.txt"),
		filepath.Join(here, "live_inbox", "inbox", "email_*.json"),
	}
	for _, p := range patterns {
		matches, _ := filepath.Glob(p)
		for _, m := range matches {
			_ = os.Remove(m)
		}
	}
	attDir := filepath.Join(here, "live_inbox", "attachments")
	entries, _ := os.ReadDir(attDir)
	for _, e := range entries {
		if e.Name() == ".gitkeep" {
			continue
		}
		_ = os.RemoveAll(filepath.Join(attDir, e.Name()))
	}
	fmt.Println("reset")
	return nil
}

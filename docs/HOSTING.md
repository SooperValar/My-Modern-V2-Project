# Hosting the server for other players

The server runs on Cody's PC (Ubuntu in WSL on Windows), maybe later on another computer at home.
Players connect with a client Cody hands out, which keeps itself up to date.

Checked already:
- The game listens on port 5555 on every address (`server.c`), so it can be reached from outside once the way is open.
- The control port 5556 (`console.c`) and the MyV2 Editor (8080, `--host 127.0.0.1`) only answer this computer. Never forward them.
- The client takes a server name, not only a number (`socket.c` looks names up), so a name like `yourgame.duckdns.org` works.
- The server refuses clients older than `MINVERSION` (`gendefs.h`), which the updater can use to make players update.

## 1. Let people reach the server
- [x] Check the internet connection has its own public address (no shared "carrier-grade NAT"): the router's WAN IP must match the address whatismyip.com shows. Done: it does (AT&T gateway, 192.168.1.254).
- [x] Give the PC a fixed address on the home network (DHCP reservation in the router). Done: Home Network → IP Allocation, the PC (Ethernet, 192.168.1.197) is private fixed.
- [x] Forward TCP port 5555 (only that one) on the router to the PC. Done: Firewall → NAT/Gaming, custom service "Astonia" TCP 5555.
- [x] Let the traffic from Windows reach Ubuntu (WSL). Done:
  - Mirrored networking: `%USERPROFILE%\.wslconfig` has `[wsl2]` / `networkingMode=mirrored` (so the server sees players' real addresses; a port proxy would show them all as this PC).
  - Windows Firewall rule "Astonia server 5555" (inbound TCP 5555) and the Hyper-V firewall rule "AstoniaWSL" (the gate between Windows and WSL), both made in an administrator PowerShell with `New-NetFirewallRule` / `New-NetFirewallHyperVRule`.
  - Side effect: with mirrored networking Ubuntu obeys Windows' reserved port ranges, and 8080 is in one, so the MyV2 Editor runs on another port (8090; it now picks a free one by itself).
- [x] Port check from outside: portchecker.co with the home address and port 5555 says "open". (Enter the address by hand; the site's own guess can be a proxy's address.)
- [x] A free server name that follows the home address: **myv2astonia.duckdns.org** (DuckDNS). Kept up to date by the Windows scheduled task "DuckDNS myv2astonia" every 15 minutes (`%USERPROFILE%\duckdns\duckdns-update.ps1`, log in `duckdns.log`; the token stays in that folder, never in the project).
- [x] Test from outside with a real client: a laptop on a phone's hotspot connected with the test zip and played. (On the laptop the first window was cramped (4:3); the client now opens wide, up to 16:9.)

## 2. A client to hand out
- [x] Server name and port in `client.ini` (`[server] host=`, `port=`), and the name built in as the default, so no `.bat` file is needed.
- [x] One zip with everything the client needs: `merc.exe`, `gx00.dat/.idx`, `pnglib.dat/.idx`, `GFX/`, `sfx/` in a folder "MyV2 Astonia" (22 MB). Never `merc.dat` (your own character logins) or your `client.ini`.
- [x] A short "how to start" note: `README.txt` in the zip (copy in `client/package/`): starting, the Windows warning, making a character, saving it as a .moa, the window, problems.

## 3. A self-updating client
- [x] A small launcher players open: `Launcher.exe` (source `client/launcher/`). Reads the file list, downloads only what changed, updates itself, then starts the game.
- [x] The files on GitHub: the `client-dist` branch of this (public) project, read from raw.githubusercontent.com. To publish an update: `python3 tools/release/publish_client.py <Client folder> <project> "<version>"`, then `git push origin client-dist`.
- [x] Launcher tested: a fresh copy of the zip checked all files and started the game (version 1); after publishing version 2 (one README line) it downloaded just that file and started the game.
- [x] The player download: `MyV2-Astonia.zip` in the Client folder (the "MyV2 Astonia" folder: Launcher.exe, merc.exe, graphics, sounds, README.txt). Rebuild it now and then so new players start close to the newest version; the launcher fetches the rest.
- **Whenever player files change** (a new `merc.exe`, new or changed sprites in `GFX/`, sounds, the README): run `publish_client.py`, then `git push origin client-dist`. Players get it the next time they start the launcher (GitHub's cache: a few minutes).
- [ ] Raising `MINVERSION` on the server makes old clients say "please update" (only needed when a client change must be in place before playing; the launcher usually updates first anyway).

## 4. Before strangers play
- [x] Automatic backups of the game data, with a copy off the PC (Nov 6). The editor (mapedit.py) zips `.dat/*.dat` (about 7 MB) at 0, 6, 12 and 18 o'clock while it runs, into `~/myv2-backups` in Ubuntu and `D:\MyV2 Backups` (`--backup-dir`; "" turns them off): `recent\` every one (last 8, two days), `daily\` the 6 o'clock one (14 days), `weekly\` Sunday's (8 weeks); `backup.log` in both. Claude can start one with the control action `backup`. **To restore**: stop the server, then in Ubuntu `cd ~ && tar xzf "/mnt/d/MyV2 Backups/daily/myv2-<date>.tar.gz"` (puts the files back into `~/.dat`), and start it. Backups need the editor running: see the next step.
- [ ] The server starts with Windows (it already restarts itself after a crash with `./server loop`). Built Nov 6, waiting for Cody to run `Server\setup-autostart.cmd` as administrator: the scheduled task "MyV2 Server" runs `myv2-autostart.vbs` (hidden) one minute after he logs on, which runs `myv2-start.sh` in Ubuntu: the editor with `--start-server` (it starts the game if it isn't running, and makes the backups), output in `~/editor.log`. If the editor already runs, the script just waits. Sources in `tools/hosting/`. Caveat: only after Cody logs on (after a reboot nothing runs until then; Windows automatic sign-in would cover that). Shutting Windows down stops the game without its normal save: see TODO 17.
- [ ] A test copy of the server for experiments, so live editing never surprises players.
- [ ] Accounts: how new players get a character and password; muting, kicking and banning (most exist in game and in the editor's Players page).
- [ ] Safety: the server runs as an ordinary user, never root; a look over the network code for unsafe input handling; tell players the game's passwords are not encrypted, so don't reuse a real one.
- [ ] Remove or lock test characters; check who has god / imp rights.
- [ ] A place for the players: e.g. a Discord with a server status page.

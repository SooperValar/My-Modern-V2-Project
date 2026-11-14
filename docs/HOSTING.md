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
- [x] One zip with everything the client needs: `merc.exe`, `gx00.dat/.idx`, `pnglib.dat/.idx`, `GFX/`, `sfx/` in a folder "MyV2 Astonia" (22 MB; from Nov 7 the folder is "Mercenaries of Asgard v2"). Never `merc.dat` (your own character logins) or your `client.ini`.
- [x] A short "how to start" note: `README.txt` in the zip (copy in `client/package/`): starting, the Windows warning, making a character, saving it as a .moa, the window, problems.

## 3. A self-updating client
- [x] A small launcher players open: `Launcher.exe` (source `client/launcher/`). Reads the file list, downloads only what changed, updates itself, then starts the game.
- [x] The files on GitHub: the `client-dist` branch of this (public) project, read from raw.githubusercontent.com. To publish an update: `python3 tools/release/publish_client.py <Client folder> <project> "<version>"`, then `git push origin client-dist`.
- [x] Launcher tested: a fresh copy of the zip checked all files and started the game (version 1); after publishing version 2 (one README line) it downloaded just that file and started the game.
- [x] The player download: `Client\For Players\Mercenaries-of-Asgard-v2.zip`, rebuilt by `publish_client.py` at every publish (since Nov 7; that folder holds only the current download; before: `MyV2-Astonia.zip`) (the "Mercenaries of Asgard v2" folder: Launcher.exe, merc.exe, graphics, sounds, README.txt). Rebuild it now and then so new players start close to the newest version; the launcher fetches the rest.
- **Whenever player files change** (a new `merc.exe`, new or changed sprites in `GFX/`, sounds, the README): run `publish_client.py`, then `git push origin client-dist`. Players get it the next time they start the launcher (GitHub's cache: a few minutes).
- [ ] Raising `MINVERSION` on the server makes old clients say "please update" (only needed when a client change must be in place before playing; the launcher usually updates first anyway).

## 4. Before strangers play
- [x] Automatic backups of the game data, with a copy off the PC (Nov 6). The editor (mapedit.py) zips `.dat/*.dat` (about 7 MB) at 0, 6, 12 and 18 o'clock while it runs, into `~/myv2-backups` in Ubuntu and `D:\MyV2 Backups` (`--backup-dir`; "" turns them off): `recent\` every one (last 8, two days), `daily\` the 6 o'clock one (14 days), `weekly\` Sunday's (8 weeks); `backup.log` in both. Claude can start one with the control action `backup`. **To restore**: stop the server, then in Ubuntu `cd ~ && tar xzf "/mnt/d/MyV2 Backups/daily/myv2-<date>.tar.gz"` (puts the files back into `~/.dat`), and start it. Backups need the editor running: see the next step.
- [ ] The server starts with Windows (it already restarts itself after a crash with `./server loop`). Built Nov 6; Cody ran `Server\setup-autostart.cmd`; still to test with a Windows restart (then tick this): the scheduled task "MyV2 Server" runs `myv2-autostart.vbs` (hidden) one minute after he logs on, which runs `myv2-start.sh` in Ubuntu: the editor with `--start-server` (it starts the game if it isn't running, and makes the backups), output in `~/editor.log`. If the editor already runs, the script just waits. Sources in `tools/hosting/`. Caveat: only after Cody logs on (after a reboot nothing runs until then; Windows automatic sign-in would cover that). Shutting Windows down stops the game without its normal save: see TODO 17.
- [ ] A test copy of the server for experiments, so live editing never surprises players.
- [x] Accounts (Nov 6): players make their own character in the client (README: don't reuse a real password). Moderation exists: `#kick`, `#shutup`, `#addban` / `#delban` / `#listban` (by address), `#black` / `#listblack`, `#nowho`, plus the editor's Players page (reset / delete / restore). No limit on new characters per address for now (Cody's choice). Abandoned new characters (under 1 hour played, not seen for 30 days; never staff / imp / god) are deleted daily at 4 o'clock with a backup (`god_cleanup_new`, `CLEANUP_DAYS` / `CLEANUP_PLAYED` in data.h; console `charcleanup list` shows who would go; restore from the Players page's deleted list).
- [x] Safety (Nov 6): the server and editor run as the ordinary Ubuntu user `cody` (files in /home/cody), never root. Only port 5555 is forwarded; the console (5556) and the editor (8090) listen on 127.0.0.1 only. The README tells players the passwords aren't encrypted. Network code review: every client message (svr_tick.c `plr_*`) checks its numbers (slots, characters, map spots via the pathfinder, shop slots), packets are fixed 16 bytes into a 256-byte buffer, player text is never used as a format string. Fixed: the account texts (name / description) now always end inside their buffer (`plr_cmd_setuser`); the build-mode tile info checks the spot is on the map (`plr_cmd_turn`); at most 5 connections at once from one internet address (`MAX_PER_ADDR`, client.h; `new_player` in server.c), so one machine can't take all 250 player slots.
- [x] Rights checked (Nov 7): only Iluvatar has god / greater god / imp / staff / builder; Testpilot and Tulkas (no rights) stay for now (Cody's choice). Keep Iluvatar's password strong and unique (not encrypted).
- [x] A place for the players: the Discord server "Mercenaries of Asgard v2" (Nov 7): INFO (read-only: #welcome with the download link and how to start, #rules, #announcements, #server-status), COMMUNITY (#general, #help, #trading, #screenshots, voice General), STAFF (private: #staff); roles Admin (administrator), Staff (kick, timeout, manage messages / nicknames, audit log), Player. Download link (always the newest release): https://github.com/SooperValar/My-Modern-V2-Project/releases/latest/download/Mercenaries-of-Asgard-v2.zip (a GitHub release per client update, asset name unchanged). Built Nov 7: the editor posts to a Discord channel webhook when the game goes down (with the reason), is offline, comes online, or restarted by itself (a crash); Claude can post with the control action `discord` ({"msg": ...}). The webhook address is secret: only in `Server\discord-webhook.txt` (one line), never in the project or git. Icon: `docs/brand/asgard-icon-helm.png`. Webhook set up Nov 7 (test post OK).

## Discord links (Nov 14)

The editor (`DiscordLink` in mapedit.py) connects the game and Discord. Each part is switched on by a file in the
**Server folder** (secret: never in git, never published); a missing file = that part off.

| File | What | How to get it |
|---|---|---|
| `discord-webhook.txt` | #server-status: up / down / crash posts (since Nov 7) | channel settings > Integrations > Webhooks > New Webhook > Copy Webhook URL |
| `discord-chat-webhook.txt` | #game-chat: in-game shouts, posted under the player's name | same, in #game-chat |
| `discord-system-webhook.txt` | #system: announcements, players entering / leaving, [Server] messages | same, in #system |
| `discord-board-webhook.txt` | #status: two messages kept up to date in place: who is online (every minute), rankings (every 10 minutes: top 10 by experience + the best 3 of each class) | same, in #status (best a read-only channel) |
| `discord-bot.txt` | Discord -> game: line 1 the bot token, line 2 the #game-chat channel id; what people write there shows in game as "[Discord] Name: text" (everyone may write; bad words refused, 200 characters) | see below |

**The bot** (only for Discord -> game): discord.com/developers/applications > New Application > Bot > Reset Token (copy it:
line 1). On the same page turn on **Message Content Intent**. OAuth2 > URL Generator: scope `bot`, permissions
*View Channels* + *Read Message History* > open the link, add it to the server. Channel id: Discord settings > Advanced >
Developer Mode on, then right-click #game-chat > Copy Channel ID (line 2). The editor reads the channel every 3 seconds
(no other program needed) and remembers where it was in `control/discord-state.json` (also the #status message ids).

**GitHub pushes** (#github): a webhook in #github, then on GitHub: the repository > Settings > Webhooks > Add webhook:
Payload URL = the Discord webhook URL with `/github` added at the end, Content type `application/json`, "Just the push
event". Nothing in the editor.

Game side (console, `console.c` / `svr_do.c`): `feed <since>` (shouts C and system messages S kept in a ring of 256),
`dshout <name> <text>`, `rankings`. Gods / imps and invisible characters are left out of the board and the rankings.

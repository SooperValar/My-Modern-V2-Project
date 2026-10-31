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
- [ ] **Next:** Test from outside with a real client (a friend's PC, or a laptop on a phone's hotspot).

## 2. A client to hand out
- [x] Server name and port in `client.ini` (`[server] host=`, `port=`), and the name built in as the default, so no `.bat` file is needed.
- [ ] One zip with everything the client needs (exe, data, GFX).
- [ ] A short "how to start" note (Windows warns about an unknown program the first time).

## 3. A self-updating client
- [ ] A small launcher players open: it reads a list of the current files (version, sizes, checksums), downloads only what changed, can update itself, then starts the game.
- [ ] The files on GitHub Releases (free, HTTPS, doesn't use the home connection); one upload per client update.
- [ ] Raising `MINVERSION` on the server makes old clients say "please update".

## 4. Before strangers play
- [ ] Automatic daily backups of the game data, with a copy off the PC.
- [ ] The server starts with Windows (it already restarts itself after a crash with `./server loop`).
- [ ] A test copy of the server for experiments, so live editing never surprises players.
- [ ] Accounts: how new players get a character and password; muting, kicking and banning (most exist in game and in the editor's Players page).
- [ ] Safety: the server runs as an ordinary user, never root; a look over the network code for unsafe input handling; tell players the game's passwords are not encrypted, so don't reuse a real one.
- [ ] Remove or lock test characters; check who has god / imp rights.
- [ ] A place for the players: e.g. a Discord with a server status page.

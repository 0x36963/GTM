# Grand Theft Mole — Game Design Document

> Status: v0.1 draft (2026-10-24). This document is the source of truth for design. Update it when decisions change.

## 1. Pitch

A heist crew of 6–12 players works a neon top-down city to pull off one big score. Hidden among them are 1–2 **Moles**: undercover cops who sabotage the plan, pick off the crew, and try to get everyone arrested.

Among Us-style social deduction set in a GTA 2-style top-down city. You steal cars, run jobs across town, and argue with each other over proximity voice.

- **Platform:** iOS and Android (mobile first, touch controls)
- **Mode:** Online multiplayer, round-based lobbies
- **Session length:** ~12 minutes per round
- **Rating target:** Mature / R. Cartoon GTA 2-style violence and crime.
- **Tone:** Chaotic, funny, crime-movie paranoia. Not gritty.

## 2. Roles

### Crew (majority)
- Run **prep jobs** to fill the Plan meter, then pull off the heist.
- No guns. They can **fight back with melee** (fists, bat, shove). Melee knocks a target down/stuns them for a few seconds and makes them drop what they're carrying. It does **not** kill.
- Can drive, steal cars, report bodies, call sit-downs, and vote.

### Moles (1–2, undercover cops)
- Look identical to crew. They see a fake job list and can pretend to do jobs.
- **Kill** with a concealed gun (cooldown) or by running people over.
- Trigger **sabotages** (see §5).
- Travel through **manholes** (the vent equivalent), moving between linked sewer entrances.
- Share a **private Mole radio** voice channel.

## 3. Round flow

```
Lobby → Role reveal → PREP PHASE → (Plan meter full) → HEIST PHASE → Escape → Results
                          ↑   sit-downs can interrupt either phase   ↑
```

1. **Lobby.** 6–12 players. The host picks settings (number of Moles, cooldowns, round timer).
2. **Role reveal.** A short splash screen: "You're Crew" or "You're the Mole" (Moles see each other).
3. **Prep phase.** The crew spreads across the city doing jobs. Each completed job fills the **Plan meter**.
4. **Heist phase.** Starts when the Plan meter is full. The bank opens, and the crew must:
   - Get inside and **drill the vault**. Players stand in drill zones together, which leaves them exposed.
   - Carry loot bags to the **getaway car**.
   - Drive the loot to the **hideout**.
5. **Results.** Roles are revealed, the winner is shown, and loot cuts are paid out.

## 4. Prep jobs (Crew tasks)

Each job is a short interaction (a mini-game or a hold-to-complete) at a location on the map. Many need travel across the city, which is what makes cars matter.

| Job | Location | Interaction |
|---|---|---|
| Steal the getaway car | Parking lot / street | Break in (lockpick mini-game), drive to hideout |
| Buy tools | Arms dealer in an alley | Pick the right items, pay |
| Case the bank | Rooftop across from the bank | Binoculars: spot guards/cameras |
| Hack the cameras | Street junction box | Wire-matching mini-game |
| Bribe a guard | Payphone | Dial the number, choose dialogue |
| Pick up the drill | Docks warehouse | Carry crate to a vehicle and deliver |
| Get blueprints | City hall records office | Find the right file drawer |
| Gas up | Gas station | Hold to fill the getaway car |

- Some jobs are **multi-step** across locations (pick up → deliver).
- **Carried items** (drill, loot) can be dropped when knocked down. Moles can steal or ditch them.
- Moles see fake jobs and can "perform" them, but these don't fill the meter.

## 5. Sabotages (Mole abilities)

Sabotages share a cooldown. Some force the crew to respond or lose.

| Sabotage | Effect | Counter |
|---|---|---|
| **Tip off the precinct** | +1 Heat star | none (just costs cooldown) |
| **Blackout** | Streetlights die and crew vision shrinks to headlights/flashlights | Two players reset breakers at the power station |
| **Tracker** | Getaway car is marked. If not removed before the heist, +2 Heat when the heist starts | Find and remove it (inspect the car) |
| **Broken drill** | Swap the drill for a dud. Discovered only at the vault | Re-do the drill pickup job |
| **Roadblocks** | Police roadblocks close some streets for a while | Drive around, or ram through for +Heat |
| **Wiretap** (critical) | Countdown starts. If not stopped in time, SWAT raid and the Moles win | Two players cut the wire at two locations at the same time |

## 6. Heat (wanted level)

A shared **0–5 star** meter, shown to everyone, taken from GTA 2's wanted level.

- **Raised by:** Mole sabotages; crew sloppiness (wrecking cars, running over civilians, starting fights in public, being seen by patrol cars).
- **Lowered by:** a few crew jobs (e.g. "lay low" at the hideout, respray a car at a garage).
- **At higher stars:** more AI patrol cars appear and chase loud players.
- **At 5 stars:** **SWAT raid**. The whole crew is arrested and the Moles win.

Heat is the main tension: the crew has to move fast but quietly, and Moles try to make them look sloppy.

## 7. Bodies, sit-downs, and voting

- **Report** a body, or hit the **alarm at the hideout** (limited uses per player), to call a **sit-down**.
- All players are teleported to a table at the hideout.
- **Discussion** (proximity voice is off, and everyone at the table hears everyone), then **vote**. Skipping is allowed.
- **Ejection:** the voted player gets **concrete shoes into the canal** (or off the harbour pier), a short cinematic. Host setting: reveal or don't reveal their role.
- Dead players become **ghosts**: they can still do jobs (crew ghosts) or sabotage (Mole ghosts), can't talk to the living, and have their own ghost voice channel.

## 8. Win conditions

**Crew wins if:**
- They escape with the loot to the hideout, or
- All Moles are ejected.

**Moles win if:**
- Heat reaches 5 stars (SWAT raid), or
- A critical sabotage (Wiretap) isn't stopped in time, or
- Living Moles ≥ living crew, or
- The round timer runs out before the heist is completed.

## 9. Combat and violence

- **Moles:** concealed pistol (instant kill, cooldown, noisy, so nearby players hear the shot and Heat goes up if a patrol car sees it). Running people over also kills.
- **Crew:** melee only. It knocks down and stuns for a few seconds, and the target drops carried items. A crew member who suspects a Mole can knock them down to make an escape or protect a teammate. Hitting an innocent wastes time and looks suspicious.
- **Civilians and traffic:** AI pedestrians and cars fill the city, GTA 2 style. Running them over is allowed (R-rated chaos) but raises Heat.
- Gore is cartoonish: splats, comic sound effects, bodies that stay as reportable markers.

## 10. Communication

- **Proximity voice chat** in the city: you hear players near you, with volume falling off over distance. Walls and buildings can muffle it (stretch goal).
- **Mole radio:** a private push-to-talk channel for Moles only.
- **Sit-down:** everyone at the table hears everyone.
- **Ghost channel:** the dead talk among themselves.
- **Quick chat / emotes** as a fallback for players without mics, shown as speech bubbles ("...", "!?", "BLA BLA").
- Must have: mute per player, report player, push-to-talk or open mic toggle.

## 11. Controls (mobile)

- **Left:** virtual joystick (on foot: direction of movement; in a car: steering with automatic throttle/brake, so pushing the stick in a direction drives that way).
- **Right:** context buttons that change with the situation: **USE** (job / enter car / manhole), **REPORT**, **ATTACK** (melee for crew, gun for Moles), **SABOTAGE** (Moles).
- **Top-left:** job list panel. **Top:** Plan meter and Heat stars.
- Buttons are large and thumb-friendly. No tank controls.

## 12. Map: v1

**Setting: tiny Amsterdam** (locked 2026-10-24). Real Amsterdam landmarks and district names, with the geography **compressed and rearranged for gameplay**, Madurodam-style. Canals, arched brick bridges, narrow gabled canal houses, cobblestones, tram tracks, houseboats, piles of bicycles, warm canal lamps, red-light neon.

- **One hand-made city, about 2×2 districts.** Kept small so players keep running into each other. Each district has a signature light colour for orientation and alibis.
  - **Canal ring (Jordaan / Prinsengracht):** hideout on a **houseboat** (meeting table, alarm), the Magere Brug, cafés. *Warm amber.*
  - **De Wallen (red-light district):** neon alleys along the Oudezijds canals, bars, the arms dealer, narrow on-foot streets. *Pink/red neon.*
  - **NDSM wharf (harbour):** graffiti-covered shipyard halls, cranes, containers, the pier, the drill pickup. Across the IJ, reached by **ferry and one bridge**, which makes it a choke point. *Cold white floodlights.*
  - **Centrum (Dam Square / Damrak / Centraal Station):** the bank (heist target) on a stone square, the Royal Palace, wide avenues, the tram hub. *Cool blue.*
  - Power station, gas station and garage/respray sit along the harbour/IJ edge.
- **Real-world rules:**
  - No real brands or logos (beer, supermarkets, GVB tram livery). Use GTA-style parodies.
  - The bank is fictional, even if its building is inspired by a real one.
  - Canal rings are straightened into angled segments so the city can be built from modular pieces.
- **Canals are terrain:** cars that drive in sink (the occupant drowns unless they get out fast), and **bridges are choke points**.
- **Trams** run on fixed lines: deadly traffic and moving cover.
- **Bikes:** stealable, quiet (no Heat from riding), slower than cars, and they fit through alleys and over narrow bridges.
- Road network with traffic, alleys for on-foot shortcuts, and a sewer network linking the manholes.
- Stretch: stealable boats on the canals.
- Lighting: night-time city. Vision is limited to a radius around you, lit by streetlights and headlights. This is the Among Us vision mechanic, and Blackout dims it further.

## 13. Progression and economy

- After each round every player gets a **cut**: more for winning, bonuses for jobs done, correct votes and survival.
- Cuts are spent on **cosmetics only**: outfits, hats, car paint, ejection styles (e.g. a car crusher instead of the pier), emote bubbles.
- **No pay-to-win.** All money is stored on the server (Nakama wallet) and changed only by the server.
- Monetization: undecided. Likely a cosmetics store / battle pass. No gameplay advantages for sale.

## 14. Art direction (locked 2026-10-24)

### Style: "Neon Grime" line art
- **Clean 2D cartoon line art**: thick dark navy/purple outlines (not pure black), flat colours, simple cel shading. Think adult animated series, not a kids' game. No texture noise.
- **Grime is put in shapes, not noise**: cracked asphalt, puddles, trash bags, graffiti, rusted shutters, stains, AC units, flickering signs.
- **Modern setting**: hoodies, puffer jackets, balaclavas, sneakers, phones, e-scooters, delivery bikes, CCTV, vape shops, LED signs.
- **Palette**: a muted, dirty concrete base; colour comes from light sources (sodium orange streetlights, pink/cyan/purple neon).
- City setting: tiny Amsterdam (see §12).
- **Style anchor:** `art/raw/style_anchor.png` (overcast, neutrally lit canal block). Use it as the reference image for all new generations. It defines outline weight, palette and level of detail, not the camera angle.
- **AI generates flat parts, the engine makes the view.** Image models can't reliably produce GTA 2's perspective, so we never ask them to. Generate orthographic pieces (roofs from straight above, facades straight-on, seamless ground textures, top-down sprites). Assembling them in 3D produces the GTA 2 view.

### Camera: GTA 2 top-down
- The camera looks **straight down with perspective**. Building walls lean outward from the screen centre (GTA 2 parallax). The camera zooms out with vehicle speed.
- **Camera tilt is tunable.** Prototype 0° (pure GTA 2) against about 15–25° from vertical to show more of the canal-house facades.
- **Characters and vehicles are single top-down sprites, rotated freely.** No directional sprite sheets.
- **Identity comes from colour and silhouette**, because faces aren't visible in the world: each player has a strong signature jacket/hoodie colour, plus hats, hair and backpacks, plus name tags.
- **Faces live in the UI**: HUD portrait, sit-down screen, voting cards, role reveal. This is where expressive character art goes.

### Lighting
- World art is drawn **flatly lit in neutral night ambient**. All mood lighting is done at runtime (streetlights, neon, headlights, vision radius). Blackout = lights off.
- Glowing parts (signs, lit windows, headlights) are separate emissive textures/masks.
- Concept images with baked lighting are mood targets only, not asset sources.

### Asset types
- **Buildings**: 3D boxes with AI-generated **roof textures** and **wall/facade textures** (tileable or per-building).
- **Ground**: road, sidewalk and alley textures/tiles on a straight grid.
- **Characters**: top-down cutout rig (head, torso, arms, legs as separate parts) animated in Godot. Cosmetics are swappable parts on the shared rig.
- **Vehicles**: one top-down sprite each (plus damage states and emissive masks for headlights/taillights).
- **Portraits**: expressive front-facing busts per cosmetic look, for the UI.
- **UI**: chunky framed panels and big icon buttons (USE / REPORT / ATTACK / SABOTAGE), bold clean font.

### Pipeline
Art is generated by the user with **Nano Banana Pro (Magnific app)** and dropped into `art/raw/`. It's then processed (background removal, optional vectorize/clean-up, resizing, trimming, atlas packing) into `assets/`. Keep a style-anchor image and use it as the reference image for new generations.

## 15. Technical overview

| Layer | Choice |
|---|---|
| Client | Godot 4, GDScript, mobile exports (iOS/Android) |
| Rendering | **3D world, 2D art.** Box buildings with roof/wall textures, flat sprites for characters/vehicles/props on the ground plane, top-down perspective camera, dynamic 3D lights. Gameplay logic stays 2D (x/y on the ground plane) |
| Game server | Server-authoritative simulation. Headless Godot build sharing client code (to be confirmed against a Nakama authoritative match handler) |
| Backend | Nakama: auth, matchmaking, lobbies, wallet, storage, cosmetics inventory |
| Voice | Proximity voice: research needed (LiveKit is the leading candidate) |
| Netcode | Server authoritative. The client predicts its own movement and driving; other players are interpolated. Roles, kills, votes and money are decided on the server only, and the server never sends clients the identity of hidden roles |

Anti-cheat principle: **clients never learn who the Moles are** unless they are a Mole. Role data stays on the server.

## 16. Milestones

1. **M0: Foundation.** Godot project, Nakama running locally in Docker, art pipeline script.
2. **M1: Movement prototype.** One city block. Two phones connect, walk, enter a car and drive. Server authoritative. *Driving feel is the main risk, so prove it first.*
3. **M2: Core loop.** Roles, 3 jobs, Plan meter, kill + report + sit-down + vote, win conditions. Placeholder art.
4. **M3: Full round.** Heist phase, Heat, sabotages, manholes, the full 2×2 city, AI traffic/civilians.
5. **M4: Voice + polish.** Proximity voice, Mole radio, lighting/vision, ejection cinematic, final art pass.
6. **M5: Meta + launch.** Accounts, cuts/wallet, cosmetics, store builds, closed beta.

## 17. Open questions

- Headless Godot server vs Nakama authoritative match handler for the simulation.
- Proximity voice provider and how it works with Godot on iOS/Android.
- Number of AI civilians/traffic a mobile device and server can handle.
- Kill/sabotage cooldown tuning, Heat rates, round timer.
- Name/trademark check: "Grand Theft Mole" closely echoes Take-Two's "Grand Theft Auto" mark.
- Legal check on depicting real Amsterdam landmarks (Dutch freedom of panorama likely covers it).

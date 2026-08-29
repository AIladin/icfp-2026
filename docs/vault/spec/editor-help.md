> [!note] Provenance
> Verbatim transcription of the **Editor Help** page at `https://icfpcontest2026.com`,
> retrieved 2026-07-24T15:13+03:00. Do not edit.

# Editor Help

## Contents

- Changing and creating programs
- The side drawer
- Editing the grid
- Typeahead (typing runs of code)
- Tools
- Running programs
- Viewport
- The menu
- The I/O panel

## Changing and creating programs

Your program's name is displayed in the upper left corner of the editor (directly to the right of "LM"). Click your program's name to access the program picker.

From here you can click on a program to swap to it, or use the pencil or trash icon to edit the program's name or delete it. All of your programs are saved to your browser's local storage.

## The side drawer

The editor contains tabs along its right side. When viewing a problem, these tabs will contain the problem's description and all of its public test cases. Another always-visible tab contains a brief language reference.

## Editing the grid

Select cells by clicking on them and type to write into them. Every cell holds one ASCII character.

- **click** — Select a cell.
- **drag** — Select an area (in the select tool).
- **arrows** — Move the selection. Shift+arrows extends it to an area.
- **Ctrl H/J/K/L** — Move the current selection (vim directions).
- **Backspace / Delete** — Clear the selected cell (in a typeahead run, also retrace: see below).
- **⌘/Ctrl C / X / V** — Copy / cut / paste. After cut/copy, a preview shows you what you would currently paste.
- **⌘/Ctrl Z** — Undo.
- **⇧⌘/Ctrl Z** — Redo (Ctrl+Y also works).
- **Escape** — One step out per press: exit typeahead, then clear the selection.

## Typeahead (typing runs of code)

To make the cursor advance as you type, press Tab to enter typeahead mode until the arrow points in your desired direction. Press escape to exit.

- **Tab** — Arm typeahead / cycle its direction (east → south → west → north). Shift+Tab cycles backwards.
- **Backspace / Delete** — Clear and back up one step.
- **Escape** — Leave typeahead mode.

## Tools

The floating palette at the bottom of the viewport switches editing modes. Hotkeys work when no cell is selected. With an area selected, `r`/`p`/`s` instead create the shape from the selection directly.

- **v** — Select — click cells, drag areas.
- **h** — Hand — drag to pan. (Holding Space also pans, from any tool.)
- **r** — Room — drag to draw a room; Esc to cancel.
- **p** — Pipe — drag to draw a pipe between two points, or click to draw a pipe between many points. Escape to cancel. Hold shift while dragging to change the pipe's orientation.
- **d** — Display — drag to draw a display.

## Running programs

- **⌘/Ctrl Enter** — Run / stop. Runs auto-play; adjust speed with the slider in the header.
- **⇧⌘/Ctrl Enter** — Run without auto-play — loads the program paused at step 0.

While a program is running (and no cell is selected):

- **p** — Play / pause.
- **n** — Next — advance one tick.
- **b** — Back — step one tick backwards.
- **+ / =** — Speed up.
- **-** — Slow down.

Select a pipe while running a program to inspect its value. Rooms and displys have collapsible widgets below them that show more debugging state. Selecting any cell that operates over a pipe highlights the pipes that it will operate over.

## Viewport

- **Space (hold)** — Pan from any tool.
- **⌘/Ctrl +** — Zoom in.
- **⌘/Ctrl -** — Zoom out.
- **⌘/Ctrl 0** — Reset zoom.

## The menu

The ⋮ menu next to the program picker allows you to copy your program to your clipboard or save it to a file.

The menu also allows you to toggle the program-flow overlay (⌥/Alt F), which traces every path a little man could walk from each starting `@` marker.

Finally, the menu has two options. Show every display frame (enabled by default) makes the editor pause for a bit when your LM-75 display shows a new frame, even if your program is running very fast. Always show raw values is only available for programs working with ASCII. It forces the UI to always use raw ints when showing you ASCII values, instead of converting them.

## The I/O panel

The bottom panel holds the program's input, the expected output, and the live output. Values are whitespace-separated integers. With expected output set, the run will stop as soon as the output matches in full or diverges.

A `/` in the input and expected boxes splits them into rounds: input for round 2 is withheld until output for round 1 has been received (and so on).

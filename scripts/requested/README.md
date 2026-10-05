# Native assembly conversion

`SOURCES.json` records the original author, assembled STEP version and checksum.
Download that exact assembled CAD from the linked upstream page; do not substitute
individual STL parts. Rook MK2 uses the beta CAD dated 2026-03-21. Satsuma uses
171223; TicTac uses the new Rat Rig toolhead assembly 040124.

The conversion requires CadQuery, OCP, NumPy and trimesh. For each input, run
`python extract_step_inventory.py source.step cache/tictac`, with the corresponding
key. Create `cache/<key>/source.json` containing the recorded `sha256` of the original
STEP. Never rescale rigid hardware. No mesh decimation is applied.

Rook's source CAD stops at the G2SA/Sherpa mount. Extract the Galileo STEP linked
in `GALILEO_SOURCE.json` into `cache/galileo`, and copy that JSON to
`cache/galileo/SOURCE.json`. Then run
`python register_g2sa.py --rook cache/rook --galileo cache/galileo`.
Galileo bodies use a separate GPL-3.0 geometry asset. The original Rook geometry
remains CC-BY-NC-4.0. Mounting-hole axes and the seating plane are registered;
missing source foot screws and clamping receivers are not fabricated.

Run `python build.py --cache cache --output output tictac rook the100 satsuma`.
The output includes complete geometry, source metadata, material roles, checksum
indexes, reference-instance lists and native validity findings. These are static
assembly references. They do not certify physical assembly, all-body clearance,
belt routing, folding, toolchanger docking or mod combinations.

# Community printer models for 3D Print Rig

Native complete-machine display assemblies for Antithesis Aether MK1.1, Rat Rig V-Minion 1.0, SnakeOil XY 180 and IDEX, SnakeOil XY-3S / KP3S, ProosaXY, Mercury One.1, VzBot 330 printed AWD, original Ender-3, SIBOOR S-BOOM, and LH Stinger 1.0 with its 200 mm carbon bed.

[Open 3D Print Rig](https://psych0h3ad.github.io/3d-print-rig/viewer/community.html?machine=antithesis_aether_mk11).

See the exact source revisions, original editable assemblies, changes, and component credits in [NOTICE](site/NOTICE.txt) and [licenses](licenses). CAD assets keep their original terms: GPL, Creative Commons, and component-specific Annex terms. No STEP downloads are generated from viewer combinations.

Author placements are retained. The controls preview offsets from each source CAD pose; they do not run firmware, homing, or mechanical belt/chain simulations. Missing source belts and wires are identified in the viewer. Reference geometry includes author calibration aids, duplicate instances and alternatives; it is optional.

Build the checked distribution: `python scripts/build_site.py --output _site`.

For the six newly added machines, extract the author's linked native STEP with `python scripts/extract_native_step.py source.step input/<machine-key>`; put the matching `source.json` record from `scripts/FAMILY_SOURCES.json` beside the inventory; then run `python scripts/convert_family.py input site <machine-key>` and `python scripts/correct_materials.py input site`. Machine keys: `aether`, `vminion`, `snake180`, `snakeidex`, `snake3s`, `proosa`. Original preferred editing sources remain available at the pinned upstream repositories and the official V-Minion share. Mesh conversion requires Python, CadQuery/OCP, NumPy, trimesh and fast-simplification.

For LH Stinger, extract the pinned STEP listed in `scripts/STINGER_SOURCE.json`, put that source record beside the resulting `inventory.json`, and run `python scripts/build_stinger.py --cache input/stinger --output output/stinger`. The native Dragon extension adapter and matching extended nozzle are displayed; the short nozzle and assembly aids are optional reference geometry.

SOVOL SV08 350 uses the manufacturer's full assembled CAD under GPL-3.0. Its 719-part display mesh preserves native tessellation without decimation, including fans, threads and rails. It is a static assembly reference with palette, camera and image-export controls. The original source omits XY belts. To reproduce: extract the STEP pinned in `scripts/SV08_SOURCE.json` into `input/sv08`, then run `python scripts/build_sv08.py --cache input/sv08 --output site/sv08-v2`. Placement overrides are in `scripts/SV08_PLACEMENTS.json`; native inspection scope is in `reviews/SV08_NATIVE_QA.json`.

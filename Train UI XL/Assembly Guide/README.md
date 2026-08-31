<div align="center">

# Train UI XL Assembly Guide

### Step-by-step enclosure and electronics assembly

[![Parts reference](images/parts-reference.jpg)](images/parts-reference.jpg)

<strong>Quick navigation:</strong><br>
[Parts](../README.md#parts) | [Step 1: Faceplate and screen](#step-1--prepare-the-front-faceplate-and-install-the-screen) | [Step 2: Middle plate and Pi Zero W](#step-2--prepare-the-middle-plate-and-mount-the-raspberry-pi-zero-w) | [Step 3: USB-C power inlet](#step-3--build-and-install-the-usb-c-power-inlet) | [Step 4: Final assembly](#step-4--square-and-close-the-enclosure)

</div>

---

This guide covers the physical Train UI XL build in order. Keep the [bill of materials](../README.md#parts) nearby while working; the individual listing photos are also stored in [`images/parts/`](images/parts/) so they remain available if an Amazon listing changes or disappears.

## Step 1 — Prepare the front faceplate and install the screen

Start with the printed front faceplate—the enclosure piece with the large opening for the display. This step adds the four threaded mounting points and seats the screen in the faceplate.

You will need:

- 1 printed front faceplate
- 4 M3 × 4 mm heat-set threaded inserts
- Heat-set insert tip and soldering iron
- 10.1-inch display

> [!CAUTION]
> Heat only one insert at a time. Keep the tip straight and use light downward pressure; too much heat or force can enlarge the hole, push the insert below the surface, or warp the faceplate. Let every insert and the surrounding plastic cool before test-fitting hardware.

### 1. Install the four heat-set inserts

The bare faceplate starts with one insert hole near each corner, as shown below.

<p align="center">
  <a href="images/steps/01-faceplate-before-inserts.jpg"><img src="images/steps/01-faceplate-before-inserts.jpg" width="300" alt="Train UI XL front faceplate before installing the heat-set inserts"></a>
</p>

Place one M3 × 4 mm heat-set insert squarely over a corner hole. With the insert tip heated, press the insert straight into the plastic until its top is level with the faceplate surface. Remove the tip without twisting the insert, allow it to cool, and repeat for the other three corners.

When finished, all four inserts should sit straight and flush like the completed faceplate below.

<p align="center">
  <a href="images/steps/02-faceplate-with-inserts.jpg"><img src="images/steps/02-faceplate-with-inserts.jpg" width="760" alt="Train UI XL front faceplate with four M3 by 4 millimeter heat-set inserts installed"></a>
</p>

### 2. Seat the display in the faceplate

After the inserts have cooled, place the faceplate front-side down on a clean, soft surface. Lower the display into the opening from the rear, with the viewing side facing the front of the enclosure and the display's rear metal panel and controller board facing you. Keep pressure off the LCD, controller board, and orange ribbon cable.

Check that the display sits flat and evenly inside the recessed edge of the faceplate, matching the orientation shown below. The four heat-set inserts should remain visible at the faceplate corners for the later enclosure-fastening steps.

<p align="center">
  <a href="images/steps/03-screen-seated-in-faceplate.jpg"><img src="images/steps/03-screen-seated-in-faceplate.jpg" width="760" alt="Rear view of the Train UI XL display seated in the front faceplate"></a>
</p>

At the end of Step 1, the front faceplate should contain four cooled, flush inserts and the display should be fully seated without pinching the ribbon cable.

## Step 2 — Prepare the middle plate and mount the Raspberry Pi Zero W

The middle plate is the printed part that will be sandwiched between the front faceplate and the back plate. In this step, install the four threaded mounting points for the Raspberry Pi Zero W, bolt the Pi to the plate, and route its cables so the back plate can close.

You will need:

- 1 printed middle plate
- 4 M2 × 4 mm heat-set threaded inserts
- Heat-set insert tip and soldering iron
- Raspberry Pi Zero W
- 4 matching M2 screws

### 1. Install the four Raspberry Pi inserts

Orient the bare middle plate as shown below, with the large rectangular display opening toward the upper left. The four small pilot holes grouped together in the bottom-left area are the Raspberry Pi mounting holes. Do not confuse them with the larger enclosure holes around the outside edge.

<p align="center">
  <a href="images/steps/04-middle-plate-before-inserts.jpg"><img src="images/steps/04-middle-plate-before-inserts.jpg" width="760" alt="Train UI XL middle plate before installing the Raspberry Pi mounting inserts"></a>
</p>

Place one M2 × 4 mm heat-set insert squarely over a Raspberry Pi mounting hole. Press it straight into the plastic until the top is flush with the plate, remove the heated tip without twisting, and let the plastic cool. Repeat for the remaining three holes.

All four inserts should be straight, flush, and arranged in the same rectangular pattern shown here:

<p align="center">
  <a href="images/steps/05-middle-plate-with-pi-inserts.jpg"><img src="images/steps/05-middle-plate-with-pi-inserts.jpg" width="760" alt="Train UI XL middle plate with four M2 by 4 millimeter Raspberry Pi mounting inserts installed"></a>
</p>

### 2. Mount and wire the Raspberry Pi Zero W

Let the inserts cool completely, place the Raspberry Pi Zero W over them, and start all four M2 screws before tightening any one screw. Tighten them only until the board is secure; overtightening can bend the Pi or pull an insert out of the printed plate.

> [!IMPORTANT]
> The Raspberry Pi must be installed in the exact orientation shown below or the back plate will not fit correctly. In this view, the middle plate has been rotated so the display opening and controller board are along the bottom, the Pi is at the upper right, and the green underside of the Pi faces outward. Its connector edge points down toward the display wiring.

Connect and route the HDMI and USB/power cables as shown. Keep every cable low and inside the open area of the middle plate—not across the outside edge, enclosure screw holes, or raised sections where the back plate sits. Before final assembly, place the back plate over the build without forcing it to confirm that the Pi and cable loops have enough clearance.

<p align="center">
  <a href="images/steps/06-pi-zero-w-mounted-and-wired.jpg"><img src="images/steps/06-pi-zero-w-mounted-and-wired.jpg" width="760" alt="Correct Raspberry Pi Zero W orientation and cable routing on the Train UI XL middle plate"></a>
</p>

At the end of Step 2, the middle plate should have four cooled M2 inserts, the Raspberry Pi Zero W should be firmly mounted in the pictured orientation, and the connected cables should remain below the back-plate mating surface.

## Step 3 — Build and install the USB-C power inlet

This step turns a Micro-USB lead into the internal, power-only cable between the enclosure's USB-C inlet and the Raspberry Pi Zero W. Only the 5-volt and ground conductors are used.

You will need:

- Printed back plate
- USB-C female panel-mount socket board
- Sacrificial USB-C-to-Micro-USB adapter lead or other Micro-USB male cable
- Wire cutters and wire strippers
- Soldering iron, solder, and a safe iron stand
- Multimeter
- Heat-shrink tubing or other suitable insulation
- Fasteners for the panel-mount USB-C board

> [!WARNING]
> Disconnect every power source before cutting, stripping, soldering, or checking continuity. The red and black wire colors must still be verified with a multimeter before soldering. Reversed polarity or a short between `V` and `G` can damage the Raspberry Pi.

### 1. Feed the Micro-USB cable through the back plate

Cut off the unwanted end of the sacrificial lead while keeping the Micro-USB male plug. Strip the cut end to expose the red and black power wires. If the cable also contains data or shield conductors, trim and insulate each unused conductor separately so it cannot touch another wire or pad.

Do this **before soldering**: feed the cut, stripped end through the small cable opening in the printed back plate. Leave the Micro-USB plug on the inside of the enclosure and the loose USB-C socket board on the outside, as shown below. The opening is only large enough for the cable—it is not large enough for the molded Micro-USB plug—so the cable cannot be added after both ends are assembled.

<p align="center">
  <a href="images/steps/07-power-cable-fed-before-soldering.jpg"><img src="images/steps/07-power-cable-fed-before-soldering.jpg" width="430" alt="Micro-USB power cable fed through the Train UI XL back plate before soldering"></a>
</p>

### 2. Solder and bolt in the USB-C socket board

The USB-C breakout has pads marked `G`, `D+`, `D-`, and `V`. This is a power-only connection:

- Solder the **red wire to `V`**.
- Solder the **black wire to `G`**.
- Leave `D+` and `D-` disconnected.

Tin the two verified wires and pads, make each joint without leaving loose strands, and insulate the finished connections. Check continuity from the Micro-USB plug to the correct pads and confirm that `V` is not shorted to `G`. Do not connect power if that short-circuit test fails.

After the joints have cooled and passed inspection, move the USB-C board into its printed opening without pulling on the wires. Bolt its panel-mount plate to the back piece so the USB-C receptacle is accessible from outside and the soldered wires remain inside. The finished joints and mounted board should match this close-up:

<p align="center">
  <a href="images/steps/08-usbc-power-board-soldered-and-mounted.jpg"><img src="images/steps/08-usbc-power-board-soldered-and-mounted.jpg" width="760" alt="Red wire soldered to V and black wire soldered to G on the mounted USB-C power board"></a>
</p>

### 3. Connect the Pi power input and check the final layout

> [!IMPORTANT]
> Plug the Micro-USB end into the Raspberry Pi port labeled **`PWR IN`**, not the `USB`/OTG port. This two-wire harness carries power only and has no USB data connection.

Route the cable in a smooth loop from the mounted USB-C inlet to the Pi without pinching it or pulling on either solder joint. Keep the cable below the back-plate mating edge and away from enclosure screw holes. The completed internal power wiring should look like the image below.

<p align="center">
  <a href="images/steps/09-finished-internal-power-wiring.jpg"><img src="images/steps/09-finished-internal-power-wiring.jpg" width="760" alt="Finished Train UI XL internal power wiring from the USB-C inlet to the Raspberry Pi Zero W power port"></a>
</p>

Before closing the enclosure or applying power, dry-fit the back plate, repeat the `V`-to-`G` short-circuit check at the USB-C inlet, and confirm that the Micro-USB plug is in `PWR IN`. At the end of Step 3, the USB-C board should be secure, its receptacle should be reachable from outside, and no wire should be trapped between printed parts.

## Step 4 — Square and close the enclosure

The final step joins the completed front faceplate, middle plate, and back plate into one enclosure.

You will need:

- Front, middle, and back assemblies from Steps 1–3
- 4 M3 × 25 mm screws
- Matching screwdriver or hex key
- A clean, flat table

### 1. Clear the closing surfaces

Keep the build disconnected from power. Check the complete perimeter, all four screw paths, and every raised mating surface before bringing the printed parts together. The HDMI and power cables must stay inside their open routing areas; no cable may cross an edge, sit over a screw hole, or become trapped between the front, middle, and back plates.

Gently place the back plate against the middle plate. If the plates will not sit together with light hand pressure, stop and reopen them. Find and move the obstruction instead of using the screws to force the enclosure closed.

### 2. Square the three printed layers

Stand the enclosure on one of its side edges on a flat table, so the front and back faces are vertical—approximately 90 degrees to the tabletop. The table provides a straight reference while you align the stack.

Press the three printed layers together evenly and adjust them until the outer edges, corners, and four screw holes line up. Keep pressure off the display itself. While holding the stack square, insert all four M3 × 25 mm screws and turn each one only a few threads so every corner is engaged before tightening.

### 3. Tighten the enclosure

Tighten the screws gradually in a diagonal pattern: one corner, the opposite corner, and then the remaining pair. Use a few turns at each corner per pass so the plates close evenly and remain square. Stop when the seams are closed and the screw heads are seated; overtightening can deform the printed parts or pull out the heat-set inserts.

The finished back should sit flat and even, with all four corners aligned like the reference below.

<p align="center">
  <a href="images/steps/10-back-plate-final-assembly.jpg"><img src="images/steps/10-back-plate-final-assembly.jpg" width="760" alt="Finished rear view of the squared and bolted Train UI XL enclosure"></a>
</p>

Perform one final perimeter check before applying power. No cable should be visible in a seam, the USB-C inlet should remain centered and accessible, and the enclosure should sit without rocking. The physical Train UI XL assembly is now complete.

# low-field
Low field MRI research group

Read reference_sheet.md to understand how g-code works. The testing folder is a bunch of tests ran to check that the g-code works, so it's not very useful now. The generate_snake.py file creates the snake.gcode which snakes around on the xy-plane and then makes a step down in the z direction.

Map_field.csv and map_pos.csv files are derived from the matlab files from the MRI4ALL github. Map
pos is the actual file that the probe has to take in and move to the positions, map field is an
example of the file we have to write out to (x mag, y mag, z mag, magnitude)
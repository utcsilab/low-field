import smbus2
import time

bus = smbus2.SMBus(1)
DEVICE_ADDRESS = 0x35 

# Registers
DEVICE_CONFIG_2 = 0x01
SENSOR_CONFIG_1 = 0x02
X_MSB_REG = 0x12

def setup_sensor():
    # Enable X, Y, and Z channels (Write 0x70 to SENSOR_CONFIG_1)
    bus.write_byte_data(DEVICE_ADDRESS, SENSOR_CONFIG_1, 0x70)
    
    # Set to Continuous Measure Mode (Write 0x02 to DEVICE_CONFIG_2)
    bus.write_byte_data(DEVICE_ADDRESS, DEVICE_CONFIG_2, 0x02)
    print("Sensor ready. Wave the magnetic rod around the chip!")

def convert_to_mt(msb, lsb, range_mt=40):
    # Combine MSB and LSB
    val = (msb << 8) | lsb
    if val > 32767:
        val -= 65536
        
    # Equation to calculate magnetic field (mT) from the datasheet
    # B = (val / 2^16) * 2 * Range
    b_mt = (val / 65536.0) * (2 * range_mt)
    return b_mt

def read_magnetic_field():
    # Read 6 bytes starting at X_MSB (0x12)
    data = bus.read_i2c_block_data(DEVICE_ADDRESS, X_MSB_REG, 6)
    
    # Convert raw data to milliteslas using the A1's default 40 mT range
    x_mt = convert_to_mt(data[0], data[1], range_mt=40)
    y_mt = convert_to_mt(data[2], data[3], range_mt=40)
    z_mt = convert_to_mt(data[4], data[5], range_mt=40)
    
    return x_mt, y_mt, z_mt

try:
    setup_sensor()
    while True:
        x, y, z = read_magnetic_field()
        # Format output to 2 decimal places for clean viewing
        print(f"\rX: {x:6.2f} mT | Y: {y:6.2f} mT | Z: {z:6.2f} mT", end="")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nTest ended.")
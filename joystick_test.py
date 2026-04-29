import smbus2
import time

# I2C address found via i2cdetect
BUS = smbus2.SMBus(1)
ADDR = 0x35 

def setup_tmag():
    # Enable X, Y, Z channels in SENSOR_CONFIG1 (0x02)
    BUS.write_byte_data(ADDR, 0x02, 0x70) 
    # Set to Continuous Measure Mode in DEVICE_CONFIG2 (0x01)
    BUS.write_byte_data(ADDR, 0x01, 0x02)
    print("Sensor initialized for joystick testing.")

def read_axes():
    # Read 6 bytes starting at 0x12 (X_MSB, X_LSB, Y_MSB, Y_LSB, Z_MSB, Z_LSB)
    data = BUS.read_i2c_block_data(ADDR, 0x12, 6)
    
    # Convert high/low bytes to signed 16-bit integers
    x = (data[0] << 8) | data[1]
    if x > 32767: x -= 65536
    
    y = (data[2] << 8) | data[3]
    if y > 32767: y -= 65536

    z = (data[4] << 8) | data[5]
    if z > 32767: z -= 65536
    
    return x, y, z

try:
    setup_tmag()
    while True:
        x, y, z = read_axes()
        print(f"Joystick Status -> X: {x} | Y: {y} | Z: {z}")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nTesting stopped.")
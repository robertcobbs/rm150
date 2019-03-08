"""Driver for the Measurement Specialties HTU21D"""

import binascii

HIH61_I2C_WRITE = "\x4E"    # Address "\x27" : [b7-b1], write bit 0: [b0]
HIH61_I2C_READ  = "\x4F"    # Address "\x27" : [b7-b1], read bit 1: [b0]

HIH61_RETRIES = 4

HIH61_ERR_VAL = -32000

HIH61_response = "/x00/x00/x00/x00"
HIH61_new_data_avail = False


def HIH61_start_conversion():
    """
    Ask the HIH61 to take a humidity & temperature reading
    """
    global HIH61_new_data_avail
    
    i2cInit(False)
    i2cWrite(HIH61_I2C_WRITE, HIH61_RETRIES, False)
    
    if getI2cResult() != 1:
        return HIH61_ERR_VAL
        
    HIH61_new_data_avail = True
    return 0

    
def _HIH61_read_data():
    """
    Returns the result from the last requested reading
    """

    global HIH61_new_data_avail, HIH61_response
    
    HIH61_response = i2cRead(HIH61_I2C_READ, 4, HIH61_RETRIES, False)
    HIH61_new_data_avail = False
    
#    print 'i2c=', dumpHex(HIH61_response)    

    if getI2cResult() != 1: # Check i2c result
        print 'i2c error'
        return False

    # Top 2 bits should be 0 for proper operation
    if ord(HIH61_response[0]) >> 6 != 0:
        print 'invalid status bits'
        return False
        
    return True
            
        
    
def HIH61_get_temp():
    """
    Returns the result from the last requested reading
    """

    global HIH61_new_data_avail, HIH61_response

    if HIH61_new_data_avail == True:
        if _HIH61_read_data() == False:
            return HIH61_ERR_VAL
            
    # temp (c) = Temperature-Output-Count/(16382) * 165 - 40
    # Below is an approximation
    temp = ((ord(HIH61_response[2]) << 6) + (ord(HIH61_response[3]) >> 2))/99 - 40
 
#    print 'temp=', temp
    
    return(temp)



def HIH61_get_humid(offset):
    """
    Returns the result from the last requested reading
    """

    global HIH61_new_data_avail, HIH61_response

    if HIH61_new_data_avail == True:
        if _HIH61_read_data() == False:
            return HIH61_ERR_VAL
            
    # humid (%RH) = Humidity-Output-Count/(16382) * 100%
    # Below is an approximation
    humid = ((ord(HIH61_response[0]) << 8) + ord(HIH61_response[1]))/164
    humid = humid + offset
#    print 'humid=', humid
    
    return(humid)

    

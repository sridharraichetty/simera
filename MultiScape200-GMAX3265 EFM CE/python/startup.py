# Start-up Script to allow interaction between the
# hardware EGSE and xScape Imager:  '>>> python -i startup.py'      OR
# software EGSE and xScape Emulator:'>>> python -i startup.py --emulator'

# Load the EGSE and xScape Imager, and other python libraries
import simera.pylibEgseFx3 as egseFx3
import simera.pylibXScape as xscape
import numpy
import time
import sys
import os

# Load the specific xScape Imaager
import simera.pylibXScape.multiscapecis200 as multiscape

# Print the Notice
try:
    from notice import *
except:
    pass;

# --- INSTANTIATE THE EGSE --- #    

if (len(sys.argv) > 1) and (sys.argv[1] == "--emulator"):
    # Import software EGSE library to communicate with xScape Emulator
    import simera.pylibEgseSw as egseFx3
    egse = egseFx3.EGSE()
    emulator = True
    egse_type = "SW "
    imager_type = "Emulated "
else:
    try:
        # If EGSE exists in the python builtins namespace (ie, it was declared by another script outside of this one), pass
        if egse != None:pass
    except NameError:
        # Else Import standard hardware EGSE library to communicate with an xScape Imager
        import simera.pylibEgseFx3 as egseFx3
        egse = egseFx3.EGSE()
    emulator = False
    egse_type = ""
    imager_type = ""
print(f'{egse_type}EGSE Loaded.')

# --- INSTANTIATE THE IMAGER --- #  

# Instantiate the xScape Imager (use the EGSE and set the I2C address for the Control Interface)
imager = multiscape.MultiScapeCIS200(EGSE=egse, I2Caddr=0x31)
print(f'{imager_type}xScape Imager Loaded.')

# --- CLIENT SPECIFIC CHOICE FOR VARIOUS INTERFACES --- #

CtrlOptions = {'pri':'I2C'}
CtrlSel = 'pri'

DataOptions = {'pri':'LVDS'}
DataSel = 'pri'

PpsOptions = {'pri':'LVCMOS_2', 'sec':'LVCMOS_2'}
PpsSel =  'pri'

# --- CLIENT SPECIFIC SETUP FOR EGSE --- #

# Setup PPS option for EGSE
egse.InitPps(pri = 'PPS_LVCMOS_2', sec = 'PPS_LVCMOS_2', polarity = 1)
egse.SelPps(PpsSel)

# Create the PPS Setup command parameter
if PpsSel == 'pri':
    imager_pps = 0x03
elif PpsSel == 'sec':
    imager_pps = 0x07
print(f'PPS Interface set to {PpsOptions[PpsSel]}')

# Set the appropriate Ctrl interface.
if CtrlOptions[CtrlSel] == 'I2C':
    imager.setControlInterfaceI2C()
print(f'Control Interface set to {CtrlOptions[CtrlSel]}')

# Set the approprate Data Interface on the EGSE
if DataOptions[DataSel] == 'LVDS':
    egse.setDataInterface(egseFx3.DATA_INTERFACE_HSDIF)
    egse.setHsMode(mode = egseFx3.HS_MODE_RX, single = True)
print(f'Data Interface set to {DataOptions[DataSel]}')
    
# Create a 'sessions' folder if it does not exist, readouts and exports are stored here
if not os.path.exists('sessions'):
    os.mkdir('sessions')
if not os.path.exists('sessions/exported_png'):
    os.mkdir('sessions/exported_png')
FilenamePrefix="sessions/"

# --- Helper Functions --- #
# -------------------------#

def PwrOn(DisableProtection=False, Bootloader=False, verbose=False):
    """    
    Power the xScape Imager ON, by enabling the EGSE Power Output.
    Allow options to disable protection and enter bootloader.
    Wait till the imager has booted.
    Note: If the SpaceWire Control Interface is required, open it.
    """
       
    # Reset the EGSE UART before power-up of the CE
    if 'uart' in globals():
        uart.Reset() 
    # Enable EGSE Power output    
    egse.PwrOut(True)
    time.sleep(0.3) # Wait about 300 ms for power-up and bootloader to start, less than 500 ms automatic boot.    
    if DisableProtection == True:
        imager.DisableProtection(0x94, 0x68, 0x39) # Disables the Protection (Latch-up, ECC and Watchdog) by issuing a command with magic numbers.        
    if Bootloader == True:
        imager.EnterBootloader() # Stops the automatic boooting of the default application.   
    else:
        if verbose: # Check how long starup takes
            time.sleep(0.2) # Wait for the Application to boot
            app_number = 0xBB # Initially we are in the bootlaoder
            t0 = time.time()
            while app_number not in [0,1,2] and (time.time() < (t0+1)):
                reset_reason, latchup_flags, app_number, run_time = imager.ReqResetStatus()
                time.sleep(0.01)        
            app_boot_time = ((time.time() - t0)*1000)
            print(f"Waited for {app_boot_time:.0f} ms for Application to start.")
            if app_number in [0,1,2]:            
                ret_dict = {'Busy': 1}  
                t0 = time.time()
                while ret_dict['Busy'] and (time.time() < (t0+2)):                
                    raw, ret_dict = imager.ReqStartupStatus()
                app_ready_time = ((time.time() - t0)*1000)    
                print(f"Waited for {app_ready_time:.0f} ms for Application to be Ready.") 
                print(f"Waited a total of {(app_boot_time + app_ready_time + 300 + 200):.0f} ms since powering ON.") # Includes the bootlaoder wait times (500ms)
        else:
            print(f"Waiting for Application to boot and Startup Status to be Ready.")
            time.sleep(1.6)
            
    # Reset egse's HSIF after power up    
    egse.HsIfReset()         

def PwrOff():
    """
    Power the xScape Imager OFF, disabling the EGSE Power Output.
    """
    egse.PwrOut(False) 

def HealthCheck(doFeeTest=False, doImageCaptureTest=False, verbose=False):
    """
    Perform a health check
    If 'verbose' is True, will print information
    If 'verbose' is False, the function will return False if health-check fails, True if it passes.
    """
    health_ok = True
    try:
        reset_reason, latchup_flags, app_number, run_time = imager.ReqResetStatus()
    except Exception as e:
        if (egse.PwrOutStat() != 1):
            # EGSE Output is OFF
            print('EGSE power output is OFF')
        else:
            print(e)
        return False
    if verbose:
        PrintImagerInformation()
        rr_str = imager.GetResetReasonString(reset_reason)
        m,s = divmod(run_time/1000, 60)
        h,m = divmod(m,60)
        print(f"Imager Running {imager.GetAppNumberString(app_number)} Application, Run Time is {run_time:>8} ms ({h:02.0f}h {m:02.0f}m {s:02.0f}s), Reset Reason is {rr_str}")
    # If Latch-up, print the latch-up flags
    if reset_reason == 0x80:
        lf_str = imager.GetLatchupFlagsString(latchup_flags)
        print(f'Latch-up Occurred on Channel(s) {lf_str}')
        health_ok = False

    if not health_ok:
        print("Imager Health Check Failed. Shutting Down.")
        PwrOff()
        PrintPowerStatus()
        return False

    mon_dict = imager.ReqMonitorCounters()
    # check for uncorrected, detected, errors count and number of watchdog resets
    for x in ['IC_DED', 'DC_DED', 'MEM_BTL_DED', 'MEM_APP_DED', 'WDT']:
        if mon_dict[x] > 0:
            print(f"FAIL: {x} set to {mon_dict[x]}")
            health_ok = False
    # check for corrected errors count
    for x in ['IC_SEC', 'DC_SEC', 'MEM_BTL_SEC', 'MEM_APP_SEC']:
        if mon_dict[x] > 0:
            print(f"WARN: {x} set to {mon_dict[x]}")
            # don't fail the health-check on corrected errors
            # uncomment next line to fail
            #health_ok = False

    if not health_ok:
        print("Imager Health Check Failed. Shutting Down.")
        PwrOff()
        PrintPowerStatus()
        return False


    ImagerLocalBootTime_t0 = time.time() - run_time/1000 + 0.1 # add 0.1s tolerance for python and OS execution variance

    imager.DisableSensor();
    time.sleep(0.3)

    current_a = egse.CurrMeas()
    imager.GetCeTelemetry()
    WaitCmdDone()
    tlm = imager.ReqCeTelemetry()    
    if not (imager.total_current_info['Range_FeeOff']['Min']/1000) <= current_a <= (imager.total_current_info['Range_FeeOff']['Max']/1000):
        print(f"EGSE 5V Supply Current : {current_a:.2f} A - Out Of Range ({imager.total_current_info['Range_FeeOff']['Min']/1000} - {imager.total_current_info['Range_FeeOff']['Max']})")
        health_ok = False
    else:
        if verbose:
            print(f"EGSE 5V Supply Current : {current_a:.2f} A - OK")
    for i in range(len(tlm)):
        tlmval = tlm[i]
        tlminfo = imager.ce_tlm_info[i]
        if tlminfo['Used']:
            if not tlminfo['Range_FeeOff']['Min'] <= tlmval <= tlminfo['Range_FeeOff']['Max']:
                print(f"CE Tlm Ch {i:>2}   {tlminfo['Name']:12} : {tlmval:>6} {tlminfo['Unit']} - Out Of Range ({tlminfo['Range_FeeOff']['Min']} to {tlminfo['Range_FeeOff']['Max']})")
                health_ok = False
            else:
                if verbose:
                    print(f"CE Tlm Ch {i:>2}   {tlminfo['Name']:12} : {tlmval:>6} {tlminfo['Unit']} - OK")

    reset_reason, latchup_flags, app_number, run_time = imager.ReqResetStatus()
    ImagerLocalBootTime = time.time() - run_time/1000
    if (ImagerLocalBootTime > ImagerLocalBootTime_t0):
        print("Imager Reset has Occurred")
        rr_str = imager.GetResetReasonString(reset_reason)
        m,s = divmod(run_time/1000, 60)
        h,m = divmod(m,60)
        print(f"Imager Running {imager.GetAppNumberString(app_number)} Application, Run Time is {run_time:>8} ms ({h:02.0f}h {m:02.0f}m {s:02.0f}s), Reset Reason is {rr_str}")
        # If Latch-up, print the latch-up flags
        if reset_reason == 0x80:
            lf_str = imager.GetLatchupFlagsString(latchup_flags)
            print(f'Latch-up Occurred on Channel(s) {lf_str}')
        health_ok = False

    if not health_ok:
        print("Imager Health Check Failed. Shutting Down.")
        PwrOff()
        PrintPowerStatus()
        return False

    temp,ret_dict = imager.ReqStartupStatus()
    if temp != 0:
        if ret_dict['Busy']:
            print("Startup Status Error - Application not Ready")
            health_ok = False
        if ret_dict['Sys']:
            print("Startup Status Error - Error Reading System Parameters")
            health_ok = False
        if ret_dict['Img']:
            print("Startup Status Error - Error Reading Imaging Parameters")
            health_ok = False
        if ret_dict['Sess']:
            print("Startup Status Error - Sess")
            sessdiag = imager.ReqSessionDiagnostics()
            print(f"\tSession Diagnostics: Error Flags = 0x{sessdiag[0]:02x}, Start Block = {sessdiag[1]}, BlockLength = {sessdiag[2]}")
            health_ok = False
        if ret_dict['Flash']:
            print("Startup Status Error - Flash")
            flashdiag = imager.ReqFlashDiagnostics()
            print(f"\tFlash Diagnostics: Status = 0x{flashdiag[0]:02x}, Failed Targets = {flashdiag[1]:>016b}b")
            health_ok = False

    if not health_ok:
        print("Imager Health Check Failed. Shutting Down.")
        PwrOff()
        PrintPowerStatus()
        return False
    else:
        if verbose:
            print("Application Startup Status - OK")

    if doFeeTest:
        if verbose:
            print("Turning on FEE")
        imager.EnableSensor()
        WaitCmdDone(3)
        time.sleep(0.2)

        reset_reason, latchup_flags, app_number, run_time = imager.ReqResetStatus()
        ImagerLocalBootTime = time.time() - run_time/1000
        if (ImagerLocalBootTime > ImagerLocalBootTime_t0):
            print("Imager Reset has Occurred")
            rr_str = imager.GetResetReasonString(reset_reason)
            m,s = divmod(run_time/1000, 60)
            h,m = divmod(m,60)
            print(f"Imager Running {imager.GetAppNumberString(app_number)} Application, Run Time is {run_time:>8} ms ({h:02.0f}h {m:02.0f}m {s:02.0f}s), Reset Reason is {rr_str}")
            # If Latch-up, print the latch-up flags
            if reset_reason == 0x80:
                lf_str = imager.GetLatchupFlagsString(latchup_flags)
                print(f'Latch-up Occurred on Channel(s) {lf_str}')
            health_ok = False

        if not health_ok:
            print("Imager Health Check Failed. Shutting Down.")
            PwrOff()
            PrintPowerStatus()
            return False

        current_a = egse.CurrMeas()
        imager.GetCeTelemetry()
        WaitCmdDone()
        tlm = imager.ReqCeTelemetry()    
        if not (imager.total_current_info['Range_FeeOn']['Min']/1000) <= current_a <= (imager.total_current_info['Range_FeeOn']['Max']/1000):
            print(f"EGSE 5V Supply Current : {current_a:.2f} A - Out Of Range ({imager.total_current_info['Range_FeeOn']['Min']/1000} - {imager.total_current_info['Range_FeeOn']['Max']/1000})")
            health_ok = False
        else:
            if verbose:
                print(f"EGSE 5V Supply Current : {current_a:.2f} A - OK")
        for i in range(len(tlm)):
            tlmval = tlm[i]
            tlminfo = imager.ce_tlm_info[i]
            if tlminfo['Used']:
                if not tlminfo['Range_FeeOn']['Min'] <= tlmval <= tlminfo['Range_FeeOn']['Max']:
                    print(f"CE Tlm Ch {i:>2}   {tlminfo['Name']:12} : {tlmval:>6} {tlminfo['Unit']} - Out Of Range ({tlminfo['Range_FeeOn']['Min']} to {tlminfo['Range_FeeOn']['Max']})")
                    health_ok = False
                else:
                    if verbose:
                        print(f"CE Tlm Ch {i:>2}   {tlminfo['Name']:12} : {tlmval:>6} {tlminfo['Unit']} - OK")

        if not health_ok:
            print("Imager Health Check Failed. Shutting Down.")
            imager.DisableSensor()
            WaitCmdDone()
            time.sleep(0.2)
            PwrOff()
            PrintPowerStatus()
            return False

        imager.GetFeeTelemetry()
        WaitCmdDone()
        tlm = imager.ReqFeeTelemetry()    
        for i in range(len(tlm)):
            tlmval = tlm[i]
            tlminfo = imager.fee_tlm_info[i]
            if tlminfo['Used']:
                if not tlminfo['Range']['Min'] <= tlmval <= tlminfo['Range']['Max']:
                    print(f"FEE Tlm Ch {i:>2}   {tlminfo['Name']:12} : {tlmval:>6} {tlminfo['Unit']} - Out Of Range ({tlminfo['Range']['Min']} to {tlminfo['Range']['Max']})")
                    health_ok = False
                else:
                    if verbose:
                        print(f"FEE Tlm Ch {i:>2}   {tlminfo['Name']:12} : {tlmval:>6} {tlminfo['Unit']} - OK")

        #turn FEE off
        if verbose:
            print("Turning off FEE")
        imager.DisableSensor()
        WaitCmdDone()
        time.sleep(0.2)

        if not health_ok:
            print("Imager Health Check Failed. Shutting Down.")
            PwrOff()
            PrintPowerStatus()
            return False

    if doImageCaptureTest:

        # save parameters so we can restore it after the test
        imager.GetImagingParameter(0x30)
        WaitCmdDone()
        lines_original = imager.ReqImagingParameter()

        #do a long line-scan capture
        imager.SetImagingParameter(0x30,12000)
        WaitCmdDone()
        imager.OpenSession()
        WaitCmdDone()
        imager.Configure(1) # Linescan mode
        WaitCmdDone(1)
        if verbose: print("Activating Session")
        imager.ActivateSession() # Automatic Mode
        WaitCmdDone(1)
        session_ID = imager.ReqCurrentSessionId()
        if verbose: print(f'Session ID {session_ID} is now Active.')
        time.sleep(1)

        if verbose:
            print("Turning on FEE")
        imager.EnableSensor()
        WaitCmdDone(3)
        time.sleep(0.2)

        imager.CaptureImage(0) # Trigger an immediate capture
        if verbose: print(f'Image Capture Triggered...')
        WaitCmdDone()

        # Calculate capture duration
        imager.GetImagingParameter(0x31)
        WaitCmdDone()
        line_period_us = imager.ReqImagingParameter()
        capture_timeout_max = (line_period_us/1000000) * (12000 + 3072); # We add everal extra lines to account for the maximum hold-off across the sensor)
        capture_timeout_max = capture_timeout_max + 1; # Add some overhead
        if emulator:capture_timeout_max = 0xEE;cap_print_note = " Note: Using Emulator, timeout not applicable" # If connected to an Emulator, don't timeout on image captures
        else:cap_print_note=""

        # Wait for Image Capture to finish
        retval, retdict = imager.ReqSubsystemStates()
        capture_state = retdict['Capture']
        start_time = time.perf_counter()
        while (health_ok) and (capture_state != 0) and ((time.perf_counter() - start_time) < capture_timeout_max):
            reset_reason, latchup_flags, app_number, run_time = imager.ReqResetStatus()
            ImagerLocalBootTime = time.time() - run_time/1000
            if (ImagerLocalBootTime > ImagerLocalBootTime_t0):
                print("Imager Reset has Occurred. {ImagerLocalBootTime:,} > {ImagerLocalBootTime_t0:,}")
                rr_str = imager.GetResetReasonString(reset_reason)
                m,s = divmod(run_time/1000, 60)
                h,m = divmod(m,60)
                print(f"Imager Running {imager.GetAppNumberString(app_number)} Application, Run Time is {run_time:>8} ms ({h:02.0f}h {m:02.0f}m {s:02.0f}s), Reset Reason is {rr_str}")
                # If Latch-up, print the latch-up flags
                if reset_reason == 0x80:
                    lf_str = imager.GetLatchupFlagsString(latchup_flags)
                    print(f'Latch-up Occurred on Channel(s) {lf_str}')
                health_ok = False
            else:
                #use 'else' clause here, else have to check for health_ok == False
                mon_dict = imager.ReqMonitorCounters()
                # check for uncorrected, detected, errors count and number of watchdog resets
                for x in ['IC_DED', 'DC_DED', 'MEM_BTL_DED', 'MEM_APP_DED', 'WDT']:
                    if mon_dict[x] > 0:
                        print(f"FAIL: {x} set to {mon_dict[x]}")
                        health_ok = False
                # check for corrected errors count
                for x in ['IC_SEC', 'DC_SEC', 'MEM_BTL_SEC', 'MEM_APP_SEC']:
                    if mon_dict[x] > 0:
                        print(f"WARN: {x} set to {mon_dict[x]}")
                        # don't fail the health-check on corrected errors
                        # uncomment next line to fail
                        #health_ok = False

            if health_ok:
                time.sleep(0.1)
                retval, retdict = imager.ReqSubsystemStates()
                capture_state = retdict['Capture']               

        # Turn FEE off
        if verbose:
            print("Turning off FEE")
        imager.DisableSensor()
        WaitCmdDone()
        time.sleep(0.2)

        imager.CloseSession()
        WaitCmdDone(0.2) 

        if (capture_state != 0):
            # Still busy, so there must have been a timeout
            print("Image Capture Timed Out")
            health_ok = False

        # report on captured size and check
        imager.GetSessionInformation(session_ID);
        WaitCmdDone()
        status, size, used = imager.ReqSessionInformation()
        if verbose:
            print(f'Session {session_ID} used {used:,} bytes of the provisioned {size:,} bytes')        
        if not (12000*9520*1.5*8) <= used <= ((12000*9520*1.5*8)*1.02):
            # Raw Size is 12000 lines, 9520 pixels, 12-bit, 8 bands
            # Compare a range here since there might be more/less ancillary packets
            # We expect the raw pixel data, with overhead of less than 2%
            print(f"Session used size is {used:,} but should be between {(12000*9520*1.5*8):,.0f} and {((12000*9520*1.5*8)*1.02):,.0f}")
            print(f"Session used size not correct")
            health_ok = False
        else:
            if verbose:
                print(f"INFO: Session used size is {used:,}")
                
        # Delete this test session
        if verbose: print(f"Deleting Session {session_ID}")
        imager.DeleteSession(session_ID)
        WaitCmdDone()

        # set parameter back to what it was
        if verbose: print(f"Reverting Number of Lines Imaging Parameter")
        imager.SetImagingParameter(0x30,lines_original)
        WaitCmdDone()

    if not health_ok:
        print("Imager Health Check Failed. Shutting Down.")
        imager.DisableSensor()
        WaitCmdDone()
        time.sleep(0.2)
        PwrOff()
        PrintPowerStatus()
        return False

    if verbose:
        print("Imager Health Check Passed.")

    return True
    
def PrintPowerStatus():
    """
    Prints a power summary of the EGSE Power output.
    """
    if (egse.PwrOutStat() != 1):
        # EGSE Output is OFF
        print('EGSE power output is OFF')
    else:
        # EGSE Output is ON
        current_ma = 1000 * egse.CurrMeas()
        print(f'EGSE power output is ON, supplying {current_ma:.1f} mA.')
        if (current_ma < 10):
            print(f'CE is not powered.')
            if (egse.GpioGet(20) == 0):
                print(f'PowerCntrl line is LOW.')
            else:
                print(f'PowerCntrl line is HIGH.')
        if (current_ma > 10) and (current_ma < 400):
            print(f'CE is powered, but FPGA is not configured, or is busy being programmed.')
        if (current_ma > 400):
            print(f'CE is powered.')

def PrintResetStatus():
    """
    Prints a reset/startup summary, including reason for reset/startup and detail about latch-up if any
    """
    reset_reason, latchup_flags, app_number, run_time = imager.ReqResetStatus()    
    rr_str = imager.GetResetReasonString(reset_reason)
    lf_str = imager.GetLatchupFlagsString(latchup_flags)
    print(f'Reset Reason   = {reset_reason} ({rr_str})')
    # If Latch-up, print the latch-up flags
    if reset_reason == 0x80:
        print(f'Latch-up Flags = 0x{latchup_flags:02x} ({lf_str})')
    if app_number == 0xBB: app_str = "Bootloader"
    if app_number == 0x00: app_str = "Factory"
    if app_number == 0x01 or app_number == 0x02: app_str = "User"   
    print(f'App Number     = {app_number} ({app_str})')                
    m,s = divmod(run_time/1000, 60)
    h,m = divmod(m,60)
    print(f'Run Time       = {run_time} ms ({h:02.0f}h {m:02.0f}m {s:02.0f}s)')

def CaptureAndReadoutSnapshot(Info=True, WithTimeSyncPPS=True, WithUserAncillaryData=True, TestPattern=False):
    """
    Capture a snapshot image, read out via Data Interface and process the data into a PNG file.

    Optional Argument:
        Info (boolean) - Print out image information (True or False)
    """
    sessionID = CaptureSnapshot(WithTimeSyncPPS=WithTimeSyncPPS, WithUserAncillaryData=WithUserAncillaryData, TestPattern=TestPattern)
    time.sleep(1)

    filename = f"snap_session_{sessionID}.bin"
    ReadOutSession(sessionID, filename)       
    print(f'Exporting images to PNG files...')
    ExportPng(filename,Info)
    print(f'Done.')
    
def CaptureAndReadoutLineScan(Info=True, WithTimeSyncPPS=True, WithUserAncillaryData=True, TestPattern=False):
    """
    Capture a linescan image, read out via Data Interface and process the data into a PNG file.

    Optional Argument:
        Info (boolean) - Print out image information (True or False)    
    """
    sessionID = CaptureLineScan(WithTimeSyncPPS=WithTimeSyncPPS, WithUserAncillaryData=WithUserAncillaryData, TestPattern=TestPattern)
    time.sleep(1)
    filename = f"line_session_{sessionID}.bin"    
    ReadOutSession(sessionID, filename)    
    print(f'Exporting images to PNG files...')
    ExportPng(filename,Info)   
    print(f'Done.')

def WaitCmdDone(timeout=0.2, verbose=False):
    """
    Waits for the current commands status to change from "busy" to "done", or times out after a speficied time (default 200ms).

    Optional Argument:
        timeout     - timeout duration in milliseconds.
    """     
    # Wait While Busy    
    start_time = time.perf_counter()
    while ((time.perf_counter() - start_time) < timeout):
        time.sleep(0.001)  
        # No longer busy?
        cmd_status = imager.ReqCommandStatus()
        if cmd_status != 1:
            break        
        
    # Report Errors   
    stop_time = time.perf_counter()        
    if (cmd_status == 1):
        # Still busy, so there must have been a timeout
        raise xscape.exceptions.Error(f'Command still busy after timeout. Waited for {stop_time-start_time} seconds. \n')        
    if (cmd_status > 1):        
        # Error code
        raise xscape.exceptions.Error(f'Command status returned an error code {cmd_status} - {imager.GetCommandStatusString(cmd_status)} \n')
    if verbose:
        print(f'Command completed in {((stop_time-start_time)*1000):.0f} ms.')

def GetAllSessionIds():
    """
    Retrieves the Session IDs of all of the Sessions stored on the imager.
    
    Retuns a list of 32-bit Session IDs.
    """
    # Generate the Session List
    print(f'Generating Session List... (Please wait)')
    imager.GenerateSessionList()
    WaitCmdDone()
    # Retrieve a single entry from the Session List
    imager.GetSessionListEntry()
    WaitCmdDone()
    session_list = []
    # Request the Session List entry value (Session ID)
    retval = imager.ReqSessionListEntry()
    i = 0
    # Loop until a zero is return (this indicates no more sessions could be found. Also this should never be more than 512
    while (retval != 0) and (i <512):
        i = i+1
        session_list.append(retval)
        imager.GetSessionListEntry() # Retireve another entry
        WaitCmdDone()
        retval = imager.ReqSessionListEntry() # Request the entry value            
    # Return the list of all the session entries found (list of Session IDs)
    return session_list
    
def GetAllSessionInformation():
    """
    Retrieves the Session IDs and Information.
    
    Retuns a dictionary of Session IDs and Informaiton.
    """
    # Request the List of Session IDs
    session_ids = GetAllSessionIds()            
    # Get the Session Information for each entry in the list
    print(f'Retrieving Session Information... (Please wait)')
    session_info = {}
    for i in range(len(session_ids)):        
        imager.GetSessionInformation(session_ids[i]);
        WaitCmdDone()
        #print(i)
        status, size, used = imager.ReqSessionInformation()          
        session_info[i] = {'ID':session_ids[i],'status':status,'size':size,'used':used}
           
    return session_info
    
def PrintAllSessionInformation():
    """
    Get and Print the Information of all of the sessions.
    """
    session_info = GetAllSessionInformation()
    if (len(session_info) == 0):
        print(f'No Sessions Found.')
    for i in range(len(session_info)):
        print(f'Session {(session_info[i]["ID"]):>3} : {(session_info[i]["used"]):>12,} of {(session_info[i]["size"]):>12,} bytes. Status = {session_info[i]["status"]}') 

def PrintCeTlm():
    """
    Get and Print CE Telemetry
    """
    imager.GetCeTelemetry()
    WaitCmdDone()
    tlm = imager.ReqCeTelemetry()    
    print ("CE Telemetry:")
    for i in range(len(tlm)):
        tlmval = tlm[i]
        tlminfo = imager.ce_tlm_info[i]
        print(f"Tlm Ch {i:>2}  {tlminfo['Name']:12} : {tlmval:>6} {tlminfo['Unit']}")
    
def PrintCeCurrentTlm():
    """
    Get and Print the 8 current telemetry values from the CE.
    """
    imager.GetCeTelemetry()
    WaitCmdDone()
    tlm = imager.ReqCeTelemetry()    
    print ("CE Current Telemetry:")
    j = 0
    retval = []
    for i in range(len(tlm)):
        tlmval = tlm[i]
        tlminfo = imager.ce_tlm_info[i]
        if tlminfo['Unit'] == 'mA':
            print(f"Tlm Ch {i:>2} (LU Ch {j})  {tlminfo['Name']:12} : {tlmval:>6} {tlminfo['Unit']}")
            j += 1
            retval.append(tlmval)

    return retval

def PrintFeeTlm():
    """
    Get and Print FEE Telemetry
    """
    imager.GetFeeTelemetry()
    WaitCmdDone()
    tlm = imager.ReqFeeTelemetry()    
    print ("FEE Telemetry:")
    for i in range(len(tlm)):
        tlminfo = imager.fee_tlm_info[i]
        print(f"{i:>2}  {tlminfo['Name']:12} : {tlm[i]:>5} {tlminfo['Unit']}")

def PrintImagerInformation():
    """
    Get and Print the Imager Information (version nubmers).
    """
    productId, serialNum, firmwareMaj, firmwareMin, softwareMaj, softwareMin, baselineNum = imager.ReqImagerInformation()
    print(f'    Product ID      : {productId}')
    print(f'    Serial Number   : {serialNum}')
    print(f'    Firmware Version: {firmwareMaj}.{firmwareMin}')
    print(f'    Software Version: {softwareMaj}.{softwareMin}')
    print(f'    Baseline Number : {baselineNum}')
    
def PrintAllSystemParameters():
    """
    Get and Print all System Parameters.
    """
    # General System Parameters
    imager.GetSystemParameter(0x00)
    WaitCmdDone()
    print(f'Flash Targets Enabled     = 0x{imager.ReqSystemParameter():04x}')
    imager.GetSystemParameter(0x01)
    WaitCmdDone()
    print(f'Flash LUNs Disabled       = 0x{imager.ReqSystemParameter():04x}')
    imager.GetSystemParameter(0x02)
    WaitCmdDone()
    print(f'Data Interface            = {imager.ReqSystemParameter()}')   
    imager.GetSystemParameter(0x03)
    WaitCmdDone()
    print(f'Sensor Temp Cal A         = {imager.ReqSystemParameter()}')   
    imager.GetSystemParameter(0x04)
    WaitCmdDone()
    print(f'Sensor Temp Cal B         = {imager.ReqSystemParameter()}')      
    imager.GetSystemParameter(0x20)
    WaitCmdDone()
    LuEnabled = imager.ReqSystemParameter()
    imager.GetSystemParameter(0x21)
    WaitCmdDone()
    LuLimits = imager.ReqSystemParameter()
    print(f'Latch-up Channels:')
    for i in range(len(LuLimits)):
        print(f"\t{imager.LatchupChannelString(i):13}: Limit={LuLimits[i]:>4} mA", end="")
        if 0 == 2**i & LuEnabled:
            print(", Disabled")
        else:
            print(", Active")
    imager.GetSystemParameter(0x22)
    WaitCmdDone()
    print(f'Latch-up Filter Count     = {imager.ReqSystemParameter()}')    
    imager.GetSystemParameter(0x23)
    WaitCmdDone()
    print(f'Monitor ECC Setup         = 0x{imager.ReqSystemParameter():02x}')        
    imager.GetSystemParameter(0x24)
    WaitCmdDone()
    print(f'Watchdog Timer Enable     = {imager.ReqSystemParameter()}')        
    imager.GetSystemParameter(0x25)
    WaitCmdDone()
    print(f'Watchdog Timer Divisor    = {imager.ReqSystemParameter()}')        
    imager.GetSystemParameter(0x40)
    WaitCmdDone()
    print(f'SpaceWire Baud Rate                  = {imager.ReqSystemParameter()}')        
    imager.GetSystemParameter(0x41)
    WaitCmdDone()
    print(f'SpaceWire Imager Log. Addr.          = {imager.ReqSystemParameter()}')            
    imager.GetSystemParameter(0x42)
    WaitCmdDone()
    print(f'SpaceWire Control Host Log. Addr.    = {imager.ReqSystemParameter()}')            
    imager.GetSystemParameter(0x43)
    WaitCmdDone()
    routing_bytes = imager.ReqSystemParameter()
    print(f'SpaceWire Control Host Routing Bytes = {routing_bytes}')                
    imager.GetSystemParameter(0x44)
    WaitCmdDone()    
    print(f'SpaceWire Data Host Log. Addr.       = {imager.ReqSystemParameter()}')                
    imager.GetSystemParameter(0x45)
    WaitCmdDone()
    routing_bytes = imager.ReqSystemParameter()
    print(f'SpaceWire Data Host Routing Bytes    = {routing_bytes}')                
    imager.GetSystemParameter(0x46)
    WaitCmdDone()    
    print(f'SpaceWire Data Packet Protocol = {imager.ReqSystemParameter()}')      
    imager.GetSystemParameter(0x47)
    WaitCmdDone()    
    print(f'SpaceWire Data Payload Limit = {imager.ReqSystemParameter()}')

def SetupLinescanParameters(thumb=8, binning=0, lines=4000, period=212, bands=[4,4,4,4,4,4,4,4], direction=0):   
    """
    Setup Linescan Imaging Parameters.
    """
    # General Imaging Parameters
    imager.SetImagingParameter(0x00,thumb)    
    WaitCmdDone()
    imager.SetImagingParameter(0x03,binning)
    WaitCmdDone()    
    # Linescan Imaging Parameters
    # Band Setup (TDI stages)
    enabled_bands = 0
    total_used_tdi = 0
    for i in range(len(bands)):
        imager.SetImagingParameter(0x32,i,bands[i])
        WaitCmdDone()
        if bands[i] > 0:
            enabled_bands += 1
            if bands[i] == 1:
                total_used_tdi += 2 # Single TDI has overhead (processing uses 2)
            else:
                total_used_tdi += bands[i]
    # Disable Unspecified Bands    
    for i in range(imager.bands-len(bands)):       
        imager.SetImagingParameter(0x32,len(bands)+i,0)
        WaitCmdDone()
    
    # Verify Maximum number of lines allowed (limitation of storage bandwidth)        
    data_rate = (enabled_bands * 13890) // period # Esitamted data rate MB/s
    print(f'Data Rate = {data_rate:.0f} Mbytes/s')
    if data_rate > 366: # Faster than flash memory / data path of 366 MB/s, apply the 1300 MB buffer limit        
        max_lines = 1300000000 // ( period * (data_rate - 366) ) # maximum scan time at line rate
        print(f'Maximum supported lines = {max_lines}')
        if lines > max_lines:
            print(f'WARNING: Number of lines ({lines}) is larger than maximum of {max_lines}.')            
    
    # Verify Total TDI Limit (S-Parameter)
    if period < 318: # Note: Value 198 used is for MultiScape200 including Image Compression. Standard product should use a value of 318
        total_tdi_limit = (period*4)//10 - 31
    else:
        total_tdi_limit = 96 # Note: Value 48 used is for MultiScape200 including Image Compression. Standard product should use a value of 96
    print(f'Total utilised TDI stages = {total_used_tdi}. Limit (S) = {total_tdi_limit:.0f}.')
    if total_used_tdi > total_tdi_limit:
        print(f'WARNING: Total Sum of utilised TDI stages ({total_used_tdi}) is larger than limit of {total_tdi_limit:.0f}.')
    
  
    # Linescan Imaging Parameters    
    imager.SetImagingParameter(0x30,lines)			    
    WaitCmdDone()
    imager.SetImagingParameter(0x31,period)
    WaitCmdDone()
    imager.SetImagingParameter(0x34,direction)
    WaitCmdDone()
    #imager.SetImagingParameter(0x39,exposure)
    #WaitCmdDone()

def PrintLinescanParameters():
    """
    Get and Print the current Linescan Imaging Parameters.
    """
    # General Imaging Parameters
    imager.GetImagingParameter(0x00)
    WaitCmdDone()
    print(f'Thumbnail Factor = {imager.ReqImagingParameter()}')    
    imager.GetImagingParameter(0x03)
    WaitCmdDone()
    print(f'Binning Factor   = {imager.ReqImagingParameter()}')    
    # Linescan Imaging Parameters
    imager.GetImagingParameter(0x30)
    WaitCmdDone()
    print(f'Lines            = {imager.ReqImagingParameter()}') 
    imager.GetImagingParameter(0x31)
    WaitCmdDone()
    print(f'Line Period      = {imager.ReqImagingParameter()}')
    imager.GetImagingParameter(0x32)
    WaitCmdDone()
    band_setup = imager.ReqImagingParameter()
    if isinstance(band_setup, list):
        for i in range(len(band_setup)):
            print(f'Band Setup {i}     = {band_setup[i]}')     
    else:
        print(f'Band Setup 0     = {band_setup}')     
    WaitCmdDone()
    band_row = imager.ReqImagingParameter()
    for i in range(len(band_row)):
        print(f'Band Start Row {i} = {band_row[i]}')
    imager.GetImagingParameter(0x34)
    WaitCmdDone()
    print(f'Scan Direction   = {imager.ReqImagingParameter()}')            
    imager.GetImagingParameter(0x35)
    WaitCmdDone()
    print(f'Black Level      = {imager.ReqImagingParameter()}')    
    imager.GetImagingParameter(0x36)
    WaitCmdDone()
    print(f'Encoding         = {imager.ReqImagingParameter()}')        
    imager.GetImagingParameter(0x37)
    WaitCmdDone()
    print(f'Encoding Offset  = {imager.ReqImagingParameter()}')     
    imager.GetImagingParameter(0x39)
    WaitCmdDone()
    print(f'Linescan Exposure Time = {imager.ReqImagingParameter()}')            

def SetupSnapshotParameters(thumb=8, binning=0, frames=1, interval=40000, encoding=10, exposure=1000):   
    """
    Setup Snapshot Imaging Parameters.
    """
    # Check Exposure Time
    if (frames > 1) and (interval < (exposure + 39000)):
        interval = exposure + 39000
        print(f"Warning: Interval Time is too low for supplied Exposure Time.")
        print(f"         Interval increased to {interval} us.")

    # General Imaging Parameters
    imager.SetImagingParameter(0x00,thumb)    
    WaitCmdDone()
    imager.SetImagingParameter(0x03,binning)    
    WaitCmdDone()    
    #Snapshot Imaging Parameters
    imager.SetImagingParameter(0x20,frames)			    
    WaitCmdDone()
    imager.SetImagingParameter(0x21,interval)
    WaitCmdDone()	
    imager.SetImagingParameter(0x22,encoding)
    WaitCmdDone()
    imager.SetImagingParameter(0x23,exposure)
    WaitCmdDone()

def PrintSnapshotParameters():
    """
    Get and Print the current Snapshot Imaging Parameters.
    """
    # General Imaging Parameters
    imager.GetImagingParameter(0x00)
    WaitCmdDone()
    print(f'Thumbnail Factor = {imager.ReqImagingParameter()}')
    imager.GetImagingParameter(0x03)
    WaitCmdDone()
    print(f'Binning Factor   = {imager.ReqImagingParameter()}')
    
    # Snapshot Imaging Parameters
    imager.GetImagingParameter(0x20)
    WaitCmdDone()
    print(f'Number of Frames = {imager.ReqImagingParameter()}')
    imager.GetImagingParameter(0x21)
    WaitCmdDone()
    print(f'Frame Interval   = {imager.ReqImagingParameter()}')
    imager.GetImagingParameter(0x22)
    WaitCmdDone()
    print(f'Encoding         = {imager.ReqImagingParameter()}')
    imager.GetImagingParameter(0x23)
    WaitCmdDone()
    print(f'Exposure Time    = {imager.ReqImagingParameter()}')
    imager.GetImagingParameter(0x24)
    WaitCmdDone()
    print(f'Encoding Offset  = {imager.ReqImagingParameter()}')
    print()    
    
def PrintAllImagingParameters():
    """
    Get and Print all Imaging Parameters.
    """
    # General Imaging Parameters
    imager.GetImagingParameter(0x00)
    WaitCmdDone()
    print(f'Thumbnail Factor    = {imager.ReqImagingParameter()}')
    imager.GetImagingParameter(0x01)
    WaitCmdDone()
    print(f'Platform ID         = {imager.ReqImagingParameter()}')    
    imager.GetImagingParameter(0x02)
    WaitCmdDone()
    print(f'Instrument ID       = {imager.ReqImagingParameter()}')    
    imager.GetImagingParameter(0x03)
    WaitCmdDone()
    print(f'Binning Factor      = {imager.ReqImagingParameter()}')
    print()    
    
    # Sensor (GMAX3265) Imaging Parameters
    imager.GetImagingParameter(0x10)
    WaitCmdDone()
    print(f'PGA Gain    = {imager.ReqImagingParameter()}')
    imager.GetImagingParameter(0x11)
    WaitCmdDone()
    print(f'ADC Gain    = {imager.ReqImagingParameter()}')    
    imager.GetImagingParameter(0x12)
    WaitCmdDone()
    print(f'Dark Offset = {imager.ReqImagingParameter()}')    
    print()
    
    # Snapshot Imaging Parameters
    imager.GetImagingParameter(0x20)
    WaitCmdDone()
    print(f'Number of Frames = {imager.ReqImagingParameter()}')    
    imager.GetImagingParameter(0x21)
    WaitCmdDone()
    print(f'Frame Interval   = {imager.ReqImagingParameter()}')    
    imager.GetImagingParameter(0x22)
    WaitCmdDone()
    print(f'Encoding         = {imager.ReqImagingParameter()}')    
    imager.GetImagingParameter(0x23)
    WaitCmdDone()
    print(f'Exposure Time    = {imager.ReqImagingParameter()}')
    imager.GetImagingParameter(0x24)
    WaitCmdDone()
    print(f'Encoding Offset  = {imager.ReqImagingParameter()}')
    print()
    
    # Linescan Imaging Parameters
    imager.GetImagingParameter(0x30)
    WaitCmdDone()
    print(f'Lines            = {imager.ReqImagingParameter()}')    
    imager.GetImagingParameter(0x31)
    WaitCmdDone()
    print(f'Line Period      = {imager.ReqImagingParameter()}')    
    imager.GetImagingParameter(0x32)
    WaitCmdDone()
    band_setup = imager.ReqImagingParameter()
    if isinstance(band_setup, list):
        for i in range(len(band_setup)):
            print(f'Band Setup {i}     = {band_setup[i]}')     
    else:
        print(f'Band Setup 0     = {band_setup}')     
    imager.GetImagingParameter(0x33)
    WaitCmdDone()
    band_row = imager.ReqImagingParameter()
    for i in range(len(band_row)):
        print(f'Band Start Row {i} = {band_row[i]}') 
    imager.GetImagingParameter(0x34)
    WaitCmdDone()
    print(f'Scan Direction   = {imager.ReqImagingParameter()}')            
    imager.GetImagingParameter(0x35)
    WaitCmdDone()
    print(f'Black Level      = {imager.ReqImagingParameter()}')    
    imager.GetImagingParameter(0x36)
    WaitCmdDone()
    print(f'Encoding         = {imager.ReqImagingParameter()}')        
    imager.GetImagingParameter(0x37)
    WaitCmdDone()
    print(f'Encoding Offset  = {imager.ReqImagingParameter()}')

def SetAllDefaultImagingParameters():
    """
    Set All of the Default Imaging Parameters.
    """
    # General Imaging Parameters
    imager.SetDefaultImagingParameter(0x00,8)
    WaitCmdDone()
    imager.SetDefaultImagingParameter(0x01,0)
    WaitCmdDone()
    imager.SetDefaultImagingParameter(0x02,0)
    WaitCmdDone()
    imager.SetDefaultImagingParameter(0x03,0)
    WaitCmdDone()    
    
    # Sensor (GMAX3265) Imaging Parameters
    imager.SetDefaultImagingParameter(0x10,125)
    WaitCmdDone()
    imager.SetDefaultImagingParameter(0x11,38)
    WaitCmdDone()  
    imager.SetDefaultImagingParameter(0x12,-685)
    WaitCmdDone()
    
    # Snapshot Imaging Parameters
    imager.SetDefaultImagingParameter(0x20,1)			    
    WaitCmdDone()
    imager.SetDefaultImagingParameter(0x21,40000)
    WaitCmdDone()	
    imager.SetDefaultImagingParameter(0x22,10)
    WaitCmdDone()
    imager.SetDefaultImagingParameter(0x23,1000)
    WaitCmdDone()
    imager.SetDefaultImagingParameter(0x24,0)
    WaitCmdDone()         
    
    # Linescan Imaging Parameters
    imager.SetDefaultImagingParameter(0x30,4000)			    
    WaitCmdDone()
    imager.SetDefaultImagingParameter(0x31,212) # Typical value for 500 km orbit height
    WaitCmdDone()	
    for i in range (imager.bands):
        imager.SetDefaultImagingParameter(0x32,i,4) # Set all bands to 4 TDI stages
        WaitCmdDone()
    imager.SetDefaultImagingParameter(0x33,0,3348) # Typical Value
    WaitCmdDone()
    imager.SetDefaultImagingParameter(0x33,1,4244) # Typical Value 
    WaitCmdDone()
    imager.SetDefaultImagingParameter(0x33,2,3872) # Typical Value
    WaitCmdDone()    
    imager.SetDefaultImagingParameter(0x33,3,3624) # Typical Value
    WaitCmdDone()
    imager.SetDefaultImagingParameter(0x33,4,2420) # Typical Value
    WaitCmdDone()
    imager.SetDefaultImagingParameter(0x33,5,2260) # Typical Value
    WaitCmdDone()
    imager.SetDefaultImagingParameter(0x33,6,1888) # Typical Value
    WaitCmdDone()
    imager.SetDefaultImagingParameter(0x33,7,2852) # Typical Value
    WaitCmdDone()
    imager.SetDefaultImagingParameter(0x34,0)
    WaitCmdDone()
    imager.SetDefaultImagingParameter(0x35,20)
    WaitCmdDone()
    imager.SetDefaultImagingParameter(0x36,12)
    WaitCmdDone()
    imager.SetDefaultImagingParameter(0x37,0)
    WaitCmdDone()

def CaptureSnapshot(Delay=0, WithTimeSyncPPS=False, WithUserAncillaryData=False, TestPattern=False):
    """
    Capture a single Snapshot using the current Imaging Parameters.

    Optional Argument:
        TestPattern     - Enable the Test pattern mode - True or False.    
        TestPattern     - Capture delay for PPS (0 = ignore PPS and capture immediately, > 1 for nubmer of PPS delays)
    """
    imager.OpenSession()
    WaitCmdDone()        

    if (TestPattern == False):
        imager.Configure(0) # Snapshot mode
    else:
        imager.Configure(2) # Snapshot Test Pattern mode
    WaitCmdDone()
    print(f'Imager Configure Done.')    

    imager.ActivateSession() # Automatic Mode
    WaitCmdDone(1)        
    session_ID = imager.ReqCurrentSessionId()        
    print(f'Session ID {session_ID} is now Active.')
    size, used = imager.ReqCurrentSessionSize()
    print(f'Session has allocated {size:,} bytes ({(size//1024//1024):,} Mbytes) for storage in Flash')

    if WithTimeSyncPPS:
        #enable PPS, and on rising edge
        imager.SetupPPS(0x03)
        #inject time sync at approximate half-second mark
        print("Injecting Time Sync Packet")
        _rem = time.time()%1
        while _rem < 0.48 or _rem > 0.5:
            time.sleep(0.01)
            _rem = time.time()%1
        imager.StoreTimeSync(Format=1, Value=int(time.time()))
    _current_time = int(time.time())

    # Check if on second mark, to inject TimeSyncPPS packet
    if int(time.time()) > _current_time :
        _current_time = int(time.time())
        if WithTimeSyncPPS:
            TriggerPPS()
            print(f'PPS occured')

    imager.EnableSensor()
    WaitCmdDone(3)       
    
    # Capture Duration
    imager.GetImagingParameter(0x20)
    WaitCmdDone()
    frames = imager.ReqImagingParameter()    
    imager.GetImagingParameter(0x21)
    WaitCmdDone()
    frame_interval = imager.ReqImagingParameter()    
    if frames > 1:
        capture_timeout = ((frame_interval/1000000) + 0.3) * frames; # Approximately 300ms overhead (time to write to flash) per frame + frame interval        
    else:
        capture_timeout = 1;    
    if emulator:capture_timeout = 0xEEE;cap_print_note = " Note: Using Emulator, timeout not applicable" # If connected to an Emulator, don't timeout on image captures
    else:cap_print_note=""
    print(f'Capturing {frames} frames at {frame_interval} us intervals. Duration is approximately {capture_timeout:.1f} seconds.{cap_print_note}')
    
    # Check if on second mark, to inject TimeSyncPPS packet
    if int(time.time()) > _current_time :
        _current_time = int(time.time())
        if WithTimeSyncPPS:
            TriggerPPS()
            print(f'PPS occured')

    imager.CaptureImage(Delay) # Trigger an immediate capture or PPS Delay
    WaitCmdDone()        
    print(f'Image Capture Triggered...')

    # Check if on second mark, to inject TimeSyncPPS packet
    if int(time.time()) > _current_time :
        _current_time = int(time.time())
        if WithTimeSyncPPS:
            TriggerPPS()
            print(f'PPS occured')

    # Simulate a PPS Trigger
    if (Delay != 0):
        for i in range(Delay):
            while int(time.time()) == _current_time:
                time.sleep(0.05)
            _current_time = int(time.time())
            #time.sleep(0.9)
            TriggerPPS()
            print(f'PPS occured: {i} of {Delay}')
        
    # Wait for Image Capture      
    retval, retdict = imager.ReqSubsystemStates()
    capture_state = retdict['Capture']
    start_time = time.perf_counter()
    while (capture_state != 0) and ((time.perf_counter() - start_time) < capture_timeout):
        if int(time.time()) > _current_time :
            # approximate 1 second mark
            _current_time = int(time.time())
            if WithTimeSyncPPS:
                TriggerPPS()
                print(f'PPS occured @ {time.time():.2f}')
            print(f'Image Capture Busy...')

        elif WithUserAncillaryData:
            _rem = time.time()%1
            if _rem > 0.47 and _rem < 0.53:
                # approximate 1/2 second mark
                l = []
                for c in f"This is sample content for a User Ancillary Data Packet ID 5 at {_current_time}":
                    l.append(ord(c))
                imager.StoreUserAncillaryData(ID=5, Payload=l)
                print(f"Injected User Ancillary Data @ {time.time():.2f}")
                time.sleep(0.05)

        time.sleep(0.05)

        retval, retdict = imager.ReqSubsystemStates()
        capture_state = retdict['Capture']               
    
    if (capture_state != 0):
        # Still busy, so there must have been a timeout
        imager.DisableSensor()
        WaitCmdDone()        
        imager.CloseSession()
        WaitCmdDone()
        raise xscape.exceptions.Error(f'Capture is still busy after timeout or error occurred.\n')            
    
    imager.DisableSensor()
    WaitCmdDone()        
    
    imager.CloseSession()
    WaitCmdDone()  
    print(f'Session is now Closed.')
    size, used = imager.ReqCurrentSessionSize()
    print(f'Session Size after capture : {used:,} bytes of {size:,} allocated bytes used')
    
    return session_ID

def CaptureLineScan(Delay=0, WithTimeSyncPPS=False, WithUserAncillaryData=False, TestPattern=False):
    """
    Capture a LineScan image using the current Imaging Parameters.

    Set TestPattern to True to capture test pattern instead of real image.
    Set Delay to implement PPS Trigger for imaging start
    Set WithTimeSyncPPS to False to not inject TimeSync packet at 1/2 second mark and TimeSyncPPS packets at 1 second mark
    Set WithUserAncillaryData to False to not inject some sample user ancillary data at 1/2 second mark
    
    Returns the Session ID
    """
    imager.OpenSession()
    WaitCmdDone()

    if (TestPattern == False):
        imager.Configure(1) # Linescan mode
    else:
        imager.Configure(3) # Linescan Test Pattern mode  
    WaitCmdDone(1)    
    print(f'Imager Configure Done.')    

    imager.ActivateSession() # Automatic Mode
    WaitCmdDone(1)        
    session_ID = imager.ReqCurrentSessionId()        
    print(f'Session ID {session_ID} is now Active.')

    if WithTimeSyncPPS:
        #enable PPS, and on rising edge
        imager.SetupPPS(0x03)
        #inject time sync at approximate half-second mark
        print("Injecting Time Sync Packet")
        _rem = time.time()%1
        while _rem < 0.48 or _rem > 0.5:
            time.sleep(0.01)
            _rem = time.time()%1
        imager.StoreTimeSync(Format=1, Value=int(time.time()))
    _current_time = int(time.time())

    # Check if on second mark, to inject TimeSyncPPS packet
    if int(time.time()) > _current_time :
        _current_time = int(time.time())
        if WithTimeSyncPPS:
            TriggerPPS()
            print(f'PPS occured')

    size, used = imager.ReqCurrentSessionSize()
    print(f'Session has allocated {size:,} bytes ({(size//1024//1024):,} Mbytes) for storage in Flash')

    # Check if on second mark, to inject TimeSyncPPS packet
    if int(time.time()) > _current_time :
        _current_time = int(time.time())
        if WithTimeSyncPPS:
            TriggerPPS()
            print(f'PPS occured')

    imager.EnableSensor()
    WaitCmdDone(3)

    # Check if on second mark, to inject TimeSyncPPS packet
    if int(time.time()) > _current_time :
        _current_time = int(time.time())
        if WithTimeSyncPPS:
            TriggerPPS()
            print(f'PPS occured')

    imager.CaptureImage(Delay) # Trigger an immediate capture or PPS Delay
    WaitCmdDone()        
    print(f'Image Capture Triggered...')

    # Check if on second mark, to inject TimeSyncPPS packet
    if int(time.time()) > _current_time :
        _current_time = int(time.time())
        if WithTimeSyncPPS:
            TriggerPPS()
            print(f'PPS occured')

    # Simulate a PPS Trigger
    if (Delay != 0):
        for i in range(Delay):
            while int(time.time()) == _current_time:
                time.sleep(0.05)
            _current_time = int(time.time())
            #time.sleep(0.9)
            TriggerPPS()
            print(f'PPS occured: {i} of {Delay}')

    # Capture Duration
    imager.GetImagingParameter(0x30)
    WaitCmdDone()
    lines = imager.ReqImagingParameter()
    imager.GetImagingParameter(0x31)
    WaitCmdDone()
    line_period_us = imager.ReqImagingParameter()    
    capture_timeout_min = (line_period_us/1000000) * lines
    capture_timeout_max = (line_period_us/1000000) * (lines + 7000) # Add everal extra lines to account for the maximum hold-off across the sensor)
    capture_timeout_max = capture_timeout_max + 4 # Allow extra time for 1300 MB buffer to be written to Flash at about 360MB/s    
    if emulator:capture_timeout_max = 0xEEE;cap_print_note = " Note: Using Emulator, timeout not applicable" # If connected to an Emulator, don't timeout on image captures
    else:cap_print_note=""
    print(f'Capturing {lines} lines at {line_period_us}us line period. Duration is between {capture_timeout_min:.1f} and {capture_timeout_max:.1f} seconds.{cap_print_note}')

    # Wait for Image Capture        
    retval, retdict = imager.ReqSubsystemStates()
    capture_state = retdict['Capture']
    start_time = time.perf_counter()
    while (capture_state != 0) and ((time.perf_counter() - start_time) < capture_timeout_max):
        if int(time.time()) > _current_time :
            # approximate 1 second mark
            _current_time = int(time.time())
            if WithTimeSyncPPS:
                TriggerPPS()
                print(f'PPS occured @ {time.time():.2f}')
            print(f'Image Capture Busy...')
        elif WithUserAncillaryData:
            _rem = time.time()%1
            if _rem > 0.47 and _rem < 0.53:
                # approximate 1/2 second mark
                l = []
                for c in f"This is sample content for a User Ancillary Data Packet ID 5 at {_current_time}":
                    l.append(ord(c))
                imager.StoreUserAncillaryData(ID=5, Payload=l)
                print(f"Injected User Ancillary Data @ {time.time():.2f}")
                time.sleep(0.05)

        time.sleep(0.05)

        retval, retdict = imager.ReqSubsystemStates()
        capture_state = retdict['Capture']               

    if (capture_state != 0):
        # Still busy, so there must have been a timeout
        imager.DisableSensor()
        WaitCmdDone() 
        imager.CloseSession()
        WaitCmdDone() 
        raise xscape.exceptions.Error(f'Capture is still busy after timeout or error occurred.\n')            
        
    imager.DisableSensor()
    WaitCmdDone()        
    
    imager.CloseSession()
    WaitCmdDone()  
    print(f'Session is now Closed.')        
    size, used = imager.ReqCurrentSessionSize()        
    print(f'Session Size after capture : {used:,} bytes of {size:,} allocated bytes used')       
    
    return session_ID

def CompressSession(SessionID, BandMask = 0xFFFFFFFF, Lossless = True, Ratio = 2.0, verbose = True):
    """
    Compress an existing session.
    
    Arguments:
        SessionID         - Original Session ID.
        Lossless (bolean) - Perform lossless compression, if false, compress to 'Ratio'
        Ratio (float)     - Rate to which we compress linedata, e.g. Ratio=2 indicates compression ratio 2:1, i.e. resulting linedata is 2x smaller.
        verbose           - Addtional printouts.
    """
    # Get Original Session Details
    imager.GetSessionInformation(SessionID)
    WaitCmdDone()
    sess_status, sess_size, sess_used = imager.ReqSessionInformation() # status, size, used
    
    if sess_status == 1:
        raise xscape.exceptions.Error(f'Original session is not closed.')
    if sess_size == 0:
        raise xscape.exceptions.Error(f'No data in original session.')
    
    # Convert compression ratio to what the imager expects
    if Lossless:
        comp_ratio = 1
    else:
        comp_ratio = Ratio * 10
        
    # Initiate Compress session
    tStart = time.perf_counter()
    imager.CompressSession(SessionID, BandMask, comp_ratio)
    WaitCmdDone(0.5)    
    
    # Calculate the Estiamted Compression Duration    
    comp_busy, band_lines, band_lines_done, bands_total, bands_done = imager.ReqCompressSessionProgress()    
    total_lines = band_lines * bands_total
    typ_rate  = 130 # Lines per second (xScape200 = 130, xScape100 = 400)
    time_expected = total_lines // typ_rate
    if Lossless:
        print(f'Requested Compression Ratio is Lossless.')
    else:
        print(f'Requested Compression Ratio: {Ratio} : 1')
    print(f'Estimated Compression Duration: {time_expected} seconds @ {typ_rate} lines/second.')
    print(f'Compression Started.')
    
    # While busy, print out lines done    
    check_bands_done = 0
    while comp_busy:
        comp_busy, band_lines_total, band_lines_done, bands_total, bands_done = imager.ReqCompressSessionProgress()
        if verbose:
            print(f'Busy - Bands Completed: {bands_done} of {bands_total} , Lines Completed: {band_lines_done} of {band_lines_total} ', end='\x1b\r')
        time.sleep(1)
       
    tStop = time.perf_counter()
    print(f'\nCompression Completed.')
    
    # Determine what session number of resultant compression is.
    comp_sess_id = imager.ReqCompressSessionId()

    # Retrieve info of compressed session
    imager.GetSessionInformation(comp_sess_id)
    WaitCmdDone()
    
    comp_sess_status, comp_sess_size, comp_sess_used = imager.ReqSessionInformation()
    
    print(f'Original Session: {sess_used:,} bytes, Compressed Session: {comp_sess_used:,} bytes.')
    # Note, will not perfectly follow Ratio, due to headers, and other data in session e.g. Thumbnails. Also, test patterns and simple images compress much more. This also assumes that all abnds in the session are compressed.
    print(f'Resulting Compression ratio: {round(sess_used/comp_sess_used,1)} : 1')        
    print(f'Actual Compression Duration: {int(tStop-tStart)} seconds @ {round(total_lines/(tStop-tStart),0)} lines/seccond.')
    
    return comp_sess_id

def ReadOutSession(SessionId, Filename, Filter=0xFFFF, FilterBands=0xFFFFFFFF):
    """
    Read Out a Session via the Data Interface.

    Mandatory Arguments:
        SessionId   (uint32) - Session Identifier of the session to read out.   
        Filename    (string) - File where the captured data is stored.        
    Optional Arguments:
        Filter      (uint16) - Filter mask for the message types.
        FilterBands (uint32) - Filter mask for the bands.
    """       
    Filename = FilenamePrefix + Filename
    imager.GetSessionInformation(SessionId);
    WaitCmdDone()
    status, size, used = imager.ReqSessionInformation()
    print(f'Read Out from Session {SessionId}: {used:,} bytes')
        
    imager.ReadOutSession(SessionId, Filter, FilterBands)    
    # Note: We cannot communicate with the Imager if Data Is being sent, since the EGSE uses the same SpaceWire interface (node) for Control and Data!              
    if not(egse.HsDataIfType == egseFx3.egse.DATA_INTERFACE_SPW):
        # Skip this command when using SpaceWire
        WaitCmdDone()
    else:    
        time.sleep(0.1)

    # Calculate EGSE HS Capture Iteration for High Speed Data Interfaces.
    if egse.HsDataIfType == egseFx3.egse.DATA_INTERFACE_USART:           
        # USART is considered slow compared to USB3 transfers
        iter_length = 1
        print(f'Reading out via USART Data Interface...')        
    else:
        # Fast Interfaces (HSDIF, etc)
        if (Filter & 0x0001) == 0:
            # Line Data is filtered out, data read will be drastically smaller, so reduce the iteration size
            used = used//10
        iter_length = used//(10*1024*1024)
        if iter_length > 64: iter_length = 64 # no speed benefit above 64 MByte chunks
        elif iter_length < 1: iter_length = 1   
        print(f'Reading out via High Speed Data Interface...')     

    # Start EGSE HS Capture
    if egse.HsDataIfType == egseFx3.egse.DATA_INTERFACE_SPW:
        if iter_length > 16: iter_length = 16 # limit spacewire to 16MB chunks
        print(f'Reading out via SpW ({iter_length}MB chunks)')
        egse.SpWCapture(filename=Filename, IterLength = iter_length*1024*1024, TimeoutFw = 1000, length=used)
    else:
        print(f'Inter Length = {iter_length}')
        egse.HsCapture(length=None, filename=Filename, IterLength = iter_length*1024*1024)
    
    # Check if Read Out is done            
    retval, retdict = imager.ReqSubsystemStates()
    read_state = retdict['Read']
    read_timeout = 1             
    start_time = time.perf_counter()
    while (read_state != 0) and ((time.perf_counter() - start_time) < read_timeout):
        time.sleep(0.001)                   
        retval, retdict = imager.ReqSubsystemStates()
        read_state = retdict['Read'] 
        
    if (read_state != 0):  
        # Still busy, so there must have been a timeout
        imager.AbortReadOut()
        WaitCmdDone()        
        raise xscape.exceptions.Error(f'Read Out is still busy after timeout or error occurred.\n') 
    
    print(f'Read Out Complete and saved to {Filename}')

def ExportPng(filename, Info=True):
    """
    Parse the image data from a bin file, and export PNG image files.

    Mandatory Arguments:    
        Filename (string)   - File where the captured data is stored.
    Optional Arguments:
        Info     (boolean)  - Print out an info summary of the image data (True or False)
        
    """
    filename = FilenamePrefix + filename
    pp = xscape.PacketParserCNP()
    pp.disableDebug()
    print(f'Reading and Parsing Data Packets from file...')
    
    pr = xscape.PacketReader(filename)
    
    for p in pr:
        pp.parsePacket(p)
    image_data = pp.ImageData()
    if Info == True:
        print(image_data)
    print(f'Generating PNG files...')
    image_data.toPng(FilenamePrefix=FilenamePrefix+'/exported_png/')   
    
def TriggerPPS():
    """
    Toggle the PPS pin.
    """
    egse.SetPps(val=1)
    time.sleep(0.1)
    egse.SetPps(val=0)
    
# --- Programming Funcitons --- #
# ----------------------------- #

def ProgramApplicationImage(AppNum, filename):
    """
    Program an application to a specified location.
    It is only possible to program the user apllications 0 or 1.
    Mandatory Arguments:  
        AppNum   (uint8)    - The allpication Nubmer (0 or 1)
        Filename (string)   - File where the captured data is stored.
    """
        
    try:
        imgFile = open(filename,"rb")
    except Exception as e:
        raise exceptions.InputError(f'Cannot open file "{filename}".\n{e}')
        
    try:
        full_img_file_data = list(imgFile.read())
    except Exception as e:
        raise exceptions.InputError(f'Error reading from file "{filename}".\n{e}')
    else:
        imgFile.close()
        
    # Check that full application image (header + data) is less than 128k    
    if len(full_img_file_data) > (128*1024):
        raise exceptions.InputError(f'Image file is too large (maximum size is 128 kbytes).\n')
    
    # Extract the header (32 bytes) and calculate the data length
    app_header = full_img_file_data[0:32]
    data_length = len(full_img_file_data) - 32
    
    # Setup the Programming
    print(f'Program Setup: App = {AppNum}')      
    imager.ProgramSetup(AppNum, app_header)
    WaitCmdDone()    
    
    # Program the application data (after the header), in chunks of 128 bytes.
    chunk_size = 128
    print(f'Programming Data... (please wait)')      
    for i in range(data_length//chunk_size):
        data_chunk = full_img_file_data[((i+0)*chunk_size)+32:((i+1)*chunk_size)+32]
        imager.ProgramData(data_chunk)
        WaitCmdDone()
        #print(f'Programming Chunk [{((i+0)*256)+32}:{((i+1)*256)+32}]')        
            
    # Program the last chunk
    last_chunk_length = data_length % chunk_size
    if last_chunk_length != 0:
        data_chunk = full_img_file_data[len(full_img_file_data)-last_chunk_length:len(full_img_file_data)] 
        imager.ProgramData(data_chunk)
        WaitCmdDone()
        #print(f'Programming Chunk [{len(full_img_file_data)-last_chunk_length}:{len(full_img_file_data)}]')        
    
    # Program Done
    imager.ProgramDone()
    WaitCmdDone()    
    
    # Print Information
    imager.GetAppHeader(AppNum)
    WaitCmdDone()
    header = imager.ReqAppHeader()
    print(f'Programming Complete: Application {AppNum}, Version {header[2]["VersionMajor"]}.{header[2]["VersionMinor"]}')
        

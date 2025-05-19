from color_setup import ssd
from gui.core.writer import Writer
from gui.core.nanogui import refresh
from gui.widgets.label import Label

import network
import time
import urequests
import json
import gui.fonts.orangeClockIcons25 as iconsSmall
import gui.fonts.orangeClockIcons35 as iconsLarge
import gui.fonts.libreFranklinSemiBold29 as large   #libreFranklinBold50
import gui.fonts.libreFranklinSemiBold29 as small
import gc
import math

wri_iconsLarge = Writer(ssd, iconsLarge, verbose=False)
wri_iconsSmall = Writer(ssd, iconsSmall, verbose=False)
wri_large = Writer(ssd, large, verbose=False)
wri_small = Writer(ssd, small, verbose=False)

rowMaxDisplay = 296
labelRow1 = 5
labelRow2 = 44
labelRow3 = 98
symbolRow1 = "A"
symbolRow2 = "H"
symbolRow3 = "C"
secretsSSID = ""
secretsPASSWORD = ""
dispVersion1 = "bh"  #bh = block height / hal = halving countdown / zap = Nostr zap counter
dispVersion2 = "mts" #mts = moscow time satsymbol / mts2 = moscow time satusd icon / mt = without satsymbol / fp1 = fiat price [$] / fp2 = fiat price [€]
npub = ""
hashrate = "0"
poolString = ""
hashString = ""
shareString = ""

def connectWIFI():
    global wifi
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    wifi.connect(secretsSSID, secretsPASSWORD)
    time.sleep(1)
    print(wifi.isconnected())


def setSelectDisplay(displayVersion1, nPub, displayVersion2):
    global dispVersion1
    global dispVersion2
    global npub
    dispVersion1 = displayVersion1
    npub = nPub
    dispVersion2 = displayVersion2


def setSecrets(SSID, PASSWORD, BITAXE_IP):
    global secretsSSID
    global secretsPASSWORD
    global secretsBitaxe_IP
    secretsSSID = SSID
    secretsPASSWORD = PASSWORD
    secretsBitaxe_IP = BITAXE_IP


def getPrice(currency): # change USD to EUR for price in euro
    gc.collect()
    data = urequests.get("https://mempool.space/api/v1/prices")
    price = data.json()[currency]
    data.close()
    return price


def getMoscowTime():
    moscowTime = str(int(100000000 / float(getPrice("USD"))))
    return moscowTime

import usocket

import ujson

def getHashrate():
    global poolString
    global hashString
    global shareString
    #print("Getting Bitaxe hashrate...")
    #print("Free memory before:", gc.mem_free())
    gc.collect()
    #print("Free memory after gc collect:", gc.mem_free())
    bitaxe_ip = secretsBitaxe_IP
    path = "/api/system/info"
    host = bitaxe_ip
    port = 80
    content_length_expected = 1001  # From headers
    max_buffer = 1500  # Safety limit to avoid over-reading
    try:
        # Create socket with timeout
        s = usocket.socket()
        s.settimeout(10.0)  # 5-second timeout
        s.connect((host, port))
        # Send HTTP request
        request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        s.send(request.encode())
        # Read response in chunks
        content = b""
        total_read = 0
        while total_read < max_buffer:
            chunk = s.recv(32)  # Even smaller chunks (32 bytes)
            if not chunk:
                #print("Connection closed early, total read:", total_read)
                break
            total_read += len(chunk)
            content += chunk
            #print("Read chunk, total length:", total_read)
            #print("Free memory after chunk:", gc.mem_free())
            gc.collect()
            # Stop if we’ve read the expected body (after headers)
            header_end = content.find(b"\r\n\r\n")
            if header_end != -1 and total_read >= header_end + 4 + content_length_expected:
                #print("Reached expected Content-Length")
                break
        s.close()
        #print("Full content length:", len(content))
        # Split headers and body
        header_end = content.find(b"\r\n\r\n")
        if header_end == -1:
            print("No header-body separator found")
            return False
        headers = content[:header_end].decode('utf-8')
        body = content[header_end + 4:].decode('utf-8')
        #print("Headers:", headers)
        #print("Raw response:", body)
        # Try parsing JSON
        try:
            response = ujson.loads(body)
            #print("Parsed response:", response)
        except Exception as e:
            print(f"JSON parsing error: {e}")
            print("Attempting to fix truncated JSON...")
            # Try fixing truncated JSON by adding closing braces
            if body.endswith('"runningPart'):
                body += 'ial"}'  # Minimal fix for your specific truncation
            elif not body.endswith('}'):
                body += '}'  # Add closing brace
            try:
                response = ujson.loads(body)
                print("Parsed fixed response:", response)
            except Exception as e:
                print(f"Fixed JSON parsing error: {e}")
                return False
        isOnFallback = response.get("isUsingFallbackStratum")
        if isOnFallback == 0:
            stratumUser = response.get("stratumUser")
            stratumURL = response.get("stratumURL")
        else:
            stratumUser = response.get("fallbackStratumUser")
            stratumURL = response.get("fallbackStratumURL")
        overheatMode = response.get("overheat_mode")
        if overheatMode == 1:
            temp =  "OVHT"
        else:
            temp = str(response.get("temp")) + "C"
        
        
        hashrate = response.get("hashRate", None)        
        bestDiff = response.get("bestDiff")
        shares = str(response.get("sharesAccepted")) + "-" + str(response.get("sharesRejected"))
        
        if "." in stratumUser:                                                                #Generate the top line poolString
            dot_index = stratumUser.find(".")  # Find position of first "."
            user = stratumUser[dot_index-6:dot_index]  # Extract 6 characters before "."
        else:
            user = "N/A"  # Fallback if no "." found
        poolString = user + "@" + stratumURL
        hashString = f"{hashrate / 1000:.1f}Th/s    " + temp  # Converts to "1.0 Th/s".   #Generate the middle, hashString
        shareString = bestDiff + "  " + shares
        print(poolString)
        print(hashString)
        print(shareString)
        
        
        print("Hashrate:", hashrate)
        return True
    except Exception as e:
        print(f"Socket error: {e}")
        s.close()
        return False

def getPriceDisplay(currency):
    price_str = f"{getPrice(currency):,}"
    if currency == "EUR":
        price_str = price_str.replace(",", ".")
    return price_str


def getLastBlock():
    gc.collect()
    data = urequests.get("https://mempool.space/api/blocks/tip/height")
    block = data.text
    data.close()
    return block


def getMempoolFees():
    gc.collect()
    data = urequests.get("https://mempool.space/api/v1/fees/recommended")
    jsonData = data.json()
    data.close()
    return jsonData


def getMempoolFeesString():
    gc.collect()
    mempoolFees = getMempoolFees()
    mempoolFeesString = (
        "L:"
        + str(mempoolFees["hourFee"])
        + " M:"
        + str(mempoolFees["halfHourFee"])
        + " H:"
        + str(mempoolFees["fastestFee"])
    )
    return mempoolFeesString


def getNostrZapCount(nPub):
    gc.collect()
    data = urequests.get("https://api.nostr.band/v0/stats/profile/"+nPub)
    jsonData = str(data.json()["stats"][str(data.json())[12:76]]["zaps_received"]["count"])
    data.close()
    return jsonData


def getNextHalving():
    return str(210000 * (math.trunc(int(getLastBlock()) / 210000) + 1) - int(getLastBlock()))


def displayInit():
    refresh(ssd, True)
    ssd.wait_until_ready()
    time.sleep(5)
    ssd._full = False
    ssd.wait_until_ready()
    refresh(ssd, True)
    ssd.wait_until_ready()
    ssd.sleep()  # deep sleep
    time.sleep(5)


def debugConsoleOutput(id):
    print("===============debug id= " + id + "===============")
    print("memory use: ", gc.mem_alloc() / 1024, "KiB")
    print("memory free: ", gc.mem_free() / 1024, "KiB")
    print("===============end debug===============")


def main():
    gc.enable()
    global wifi
    global secretsSSID
    global secretsPASSWORD
    global secretsBitaxe_IP
    global bitaxeMode
    debugConsoleOutput("1")
    issue = False
    blockHeight = ""
    textRow2 = ""
    mempoolFees = ""
    i = 1
    connectWIFI()
    displayInit()
    while True:
        debugConsoleOutput("2")
        if issue:
            issue = False
        if i > 72:
            i = 1
            refresh(ssd, True)  # awake from deep sleep
            time.sleep(5)
            ssd._full = True
            ssd.wait_until_ready()
            refresh(ssd, True)
            ssd.wait_until_ready()
            time.sleep(20)
            ssd._full = False
            ssd.wait_until_ready()
            refresh(ssd, True)
            time.sleep(5)
            
        try:
            if secretsBitaxe_IP != "":
                bitaxeMode = getHashrate() #sets this flag according to whether we successfully got data from a Bitaxe device
            else:
                bitaxeMode = False
        except Exception as err:
            blockHeight = "Bitaxe error"
            print("### Bitaxe error")
        try:
            if bitaxeMode:
                symbolRow1 = ""
                blockHeight = poolString
            elif dispVersion1 == "zap":
                symbolRow1 = "F"
                blockHeight = getNostrZapCount(npub)
            elif dispVersion1 == "hal":
                symbolRow1 = "E"
                blockHeight = getNextHalving()
            else:
                symbolRow1 = "A"
                blockHeight = getLastBlock()    
        except Exception as err:
            blockHeight = "connection error"
            symbolRow1 = ""
            print("Block: Handling run-time error:", err)
            debugConsoleOutput("3")
            issue = True
        try:
            if bitaxeMode:
                symbolRow2 = ""
                textRow2 = hashString
            elif dispVersion2 == "mt":
                symbolRow2 = ""
                textRow2 = getMoscowTime()
            elif dispVersion2 == "mts2":
                symbolRow2 = "I"
                textRow2 = getMoscowTime()
            elif dispVersion2 == "fp1":
                symbolRow2 = "K"
                textRow2 = getPriceDisplay("USD")
            elif dispVersion2 == "fp2":
                symbolRow2 = "B"
                textRow2 = getPriceDisplay("EUR")
            else:
                symbolRow2 = "H"
                textRow2 = getMoscowTime()        
        except Exception as err:
            textRow2 = "error"
            symbolRow2 = ""
            print("Moscow: Handling run-time error:", err)
            debugConsoleOutput("4")
            issue = True
        try:
            if bitaxeMode:
                symbolRow3 = ""
                mempoolFees = shareString
            else:    
                symbolRow3 = "C"
                mempoolFees = getMempoolFeesString()
        except Exception as err:
            mempoolFees = "connection error"
            symbolRow3 = ""
            print("Fees: Handling run-time error:", err)
            debugConsoleOutput("5")
            issue = True

        labels = [
            Label(
                wri_small,
                labelRow1,
                int(
                    (
                        rowMaxDisplay
                        - Writer.stringlen(wri_small, blockHeight)
                        + Writer.stringlen(wri_iconsSmall, symbolRow1)
                        + 4  # spacing
                    )
                    / 2
                ),
                blockHeight,
            ),
            Label(
                wri_iconsSmall,
                labelRow1 + 2,  # center icon with text
                int(
                    (
                        rowMaxDisplay
                        - Writer.stringlen(wri_iconsSmall, symbolRow1)
                        - Writer.stringlen(wri_small, blockHeight)
                        - 4  # spacing
                    )
                    / 2
                ),
                symbolRow1,
            ),
            Label(
                wri_large,
                labelRow2,
                int(
                    (
                        rowMaxDisplay
                        - Writer.stringlen(wri_large, textRow2)
                        + Writer.stringlen(wri_iconsLarge, symbolRow2)
                        # + 2  # spacing
                    )
                    / 2
                ),
                textRow2,
            ),
            Label(
                wri_iconsLarge,
                labelRow2,  # + 10 for centered satsymbol
                int(
                    (
                        rowMaxDisplay
                        - Writer.stringlen(wri_iconsLarge, symbolRow2)
                        - Writer.stringlen(wri_large, textRow2)
                        # - 2  # spacing
                    )
                    / 2
                ),
                symbolRow2,
            ),
            Label(
                wri_small,
                labelRow3,
                int(
                    (
                        rowMaxDisplay
                        - Writer.stringlen(wri_small, mempoolFees)
                        + Writer.stringlen(wri_iconsSmall, symbolRow3)
                        + 4  # spacing
                    )
                    / 2
                ),
                mempoolFees,
            ),
            Label(
                wri_iconsSmall,
                labelRow3 + 1,  # center icon with text
                int(
                    (
                        rowMaxDisplay
                        - Writer.stringlen(wri_iconsSmall, symbolRow3)
                        - Writer.stringlen(wri_small, mempoolFees)
                        - 4  # spacing
                    )
                    / 2
                ),
                symbolRow3,
            )
        ]

        refresh(ssd, False)
        ssd.wait_until_ready()
        ssd.sleep()
        if not issue:
            time.sleep(600)  # 600 normal

        else:
            wifi.disconnect()
            debugConsoleOutput("6")
            wifi.connect(secretsSSID, secretsPASSWORD)
            time.sleep(60)
            gc.collect()

        # Have the Labels write blanks into the framebuf to erase what they
        # rendered in the previous cycle.
        for label in labels:
            label.value("")
            
        i = i + 1

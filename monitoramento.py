from pyfirmata import Arduino, util
import time
import requests
import json

# Arduino-------------------------------------------------------------------------------------------------
arduino = Arduino('COM3')  # PORTA USB A QUAL O ARDUINO IRÁ UTILIZAR
it = util.Iterator(arduino)
it.start()

# Caixa de água-------------------------------------------------------------------------------------------
sensorNivel = arduino.get_pin('a:5:i')
sensorUmidade = arduino.get_pin('a:0:i')
gardenBomb = arduino.get_pin('d:4:o')
externalBomb = arduino.get_pin('d:2:o')
bathroomBomb = arduino.get_pin('d:3:o')
warning = False
turnOnExternal = False
useRemainingWater = False

# Dados Banheiro-------------------------------------------------------------------------------------------
bathroomBombStatus = False
turnOnbathroom = True

# Horta----------------------------------------------------------------------------------------------------
minHumidity = 0
maxHumidity = 100
minPercentage = 0
maxPercentage = 100
mult = 100
gardenBombStatus = False


def valueMap(value, istart, istop, ostart, ostop):
    return ostart + (ostop - ostart) * ((value - istart) / (istop - istart))


# Dados do Servidor----------------------------------------------------------------------------------------
urlGet = "https://arduino-aps-server.herokuapp.com/waterbox"
urlPost = "https://arduino-aps-server.herokuapp.com/waterbox/data"
currentServerData = json.loads(requests.get(urlGet).text)

while True:
    time.sleep(4)
    userWaterLevel = currentServerData['userWaterLevel']
    waterLevel = round(sensorNivel.read() or 0, 2)
    requests.post(urlPost, data={
        'waterLevel': waterLevel,
        'warning': warning,
        'totalVolume': 1500,
        'turnOnExternal': False,
        'useRemainingWater': False,
        'userWaterLevel': userWaterLevel,
        'isOnUserWaterLevel': False
    })

    print(waterLevel)
    # Se a caixa de água atingir o nível de segurança:
    if waterLevel <= 0.3:
        warning = True
        requests.post(urlPost, data={
            'waterLevel': waterLevel,
            'warning': warning,
            'totalVolume': 1500,
            'turnOnExternal': False,
            'useRemainingWater': False,
            'userWaterLevel': userWaterLevel,
            'isOnUserWaterLevel': True
        })
        time.sleep(10)

        # Vendo no front se deve ou não reabestecer a caixa:
        turnOnExternal = currentServerData['turnOnExternal']
        if turnOnExternal == True:
            while True:
                waterLevel = round(sensorNivel.read() or 0, 2)
                if waterLevel < 0.57:
                    externalBomb.write(1)
                    time.sleep(0.2)
                else:
                    externalBomb.write(0)
                    warning = False
                    requests.post(urlPost, data={
                        'waterLevel': waterLevel,
                        'warning': warning,
                        'totalVolume': 1500,
                        'turnOnExternal': False,
                        'useRemainingWater': False,
                        'userWaterLevel': userWaterLevel,
                        'isOnUserWaterLevel': True
                    })
                    break
        else:
            externalBomb.write(0)
        time.sleep(5)

    # Se o nível da caixa atingir o nível definido pelo usuário:
    elif waterLevel > 0.2 and waterLevel <= userWaterLevel:
        gardenBombStatus = False
        bathroomBombStatus = False
        # Aqui deveria enviar o dado para o servidor que a caixa atingiu o nível definido pelo usuário
        requests.post(urlPost, data={
            'waterLevel': waterLevel,
            'warning': warning,
            'totalVolume': 1500,
            'turnOnExternal': False,
            'useRemainingWater': False,
            'userWaterLevel': userWaterLevel,
            'isOnUserWaterLevel': True
        })
        # Aqui pegar no servidor o dado se deve utilizar o restante da água
        time.sleep(10)
        useRemainingWater = currentServerData['useRemainingWater']
        if useRemainingWater == True:
            gardenBombStatus = True
            bathroomBombStatus = True
    elif waterLevel >= userWaterLevel:
        bathroomBombStatus = True
        gardenBombStatus = True

    # Verificando umidade do jardim----------------------------------------------------------------------------
    while True:
        value = sensorUmidade.read()
        value = int(value * mult)
        if value >= minHumidity and value <= maxHumidity:
            humidityLevel = valueMap(
            value, maxHumidity, minHumidity, maxPercentage, minPercentage)
            print(f'Nível de umidade: {humidityLevel:.0f}%')
            value = value - value
            if humidityLevel < 30 and gardenBombStatus == True:
                gardenBomb.write(1)
                time.sleep(0.2)
            else:
                gardenBomb.write(0)
                break
        else:
            print('Valor não suportado')

    # Liga e desliga a bomba do banheiro------------------------------------------------------------------------
    if bathroomBombStatus == True:
        bathroomBomb.write(1)
    else:
        bathroomBomb.write(0)
    time.sleep(10)

import PySimpleGUI as sg
import serial
import serial.tools.list_ports
import time
import datetime
import os.path
import os
import shutil

sg.theme('Default 1')

# helper functions
def get_port_names():
    return [port.name for port in serial.tools.list_ports.comports()]

def validate_number_input(input_key, window, values):
    if len(values[input_key]) > 0 and values[input_key][-1] not in ('0123456789'):
            window[input_key].update(values[input_key][:-1])

def logging_time(file_name):
    now = datetime.datetime.now()
    date = "Logging Finished: {}.{}.{} {}:{}:{}\
        n".format(now.day, now.month, now.year, now.hour, now.minute, now.second)
    with open(file_name, "a") as file:
        file.write(date)


def write_in_file(folder_path, board_rev, samples, acquisitions, channels, data):
    for measurment in range(1, acquisitions + 1):
        file_name = 'm_{:04d}'.format(measurment)
        file_name = os.path.join(folder_path, file_name)
        with open(file_name, 'a') as file:
            file.write("#setup 0\n")
            notes = channels.len()
            file.write("#notes {} \n".format(notes))
            file.write("Board revision: 01\n") if board_rev == 'Rev01' else file.write("Board revision: 02\n")
            file.write("Firmware Version: yy.mm.ab\n")  #verzija softvera?
            logging_time(file_name)
            file.write('data {}, {}\n'.format(samples, channels))
            file.write('sample, ')
            for i in range(channels):
                file.write('ch{}, '.format(i))
            file.write('\n')

            for index, in enumerate(data):               
                file.write('{}. '.format(index+1))
                for sample in data[index]:
                    file.write("{}, ".format(sample))                
                file.write('{}\n'.format(0.0))




def serial_get_samples(port_name, no_samples, channels):
    sp = serial.Serial(port_name, 9600)
    data_received = list()

    try:
        if not sp.isOpen():
            sp.open()

        data_to_send = no_samples.to_bytes(2, byteorder='little') + bytes(channels)  #SAMPLES AND CHANNELS
        sp.write(data_to_send)

        for _ in range(no_samples):
            sample = list()
            for _ in channels:
                sample.append(int.from_bytes(sp.read(2), byteorder='little'))
            data_received.append(sample)

    except Exception as e:
        print('Error:', str(e))

    finally:
        sp.close()
        return data_received


# layouts
ch_select_layout = [
    [sg.Checkbox(i, key=f'ch{i}') for i in range(1, 4)],
    [sg.Checkbox(i, key=f'ch{i}')  for i in range(4, 7)],
    [sg.Checkbox(i, key=f'ch{i}')  for i in range(7, 9)]
]

column_layout = [
    [
        sg.Text('Samples:', size=(15, 1)), 
        sg.Text('Acquisitions:', size=(21, 1)), 
        sg.Text('Board Revision:', size=(15, 1))
    ],

    [
        sg.Input(key='-SAMPLES-', size=(15, 1), pad=((8, 20), 0), justification='center', enable_events=True),
        sg.Input(key='-ACQUISITIONS-', size=(15, 1), pad=((0, 71), 0), justification='center', enable_events=True),
        sg.Combo(['Rev01', 'Rev02'], key='-BOARD_REV-', size=(10, 1))
    ],

    [
        sg.Button('Start', button_color=('white', '#008CFF'), pad=((321, 0), (15, 0)), size=(10, 1))
    ]
]

layout = [
    [   
        sg.Text('Log Files Folder:', size=(15, 1)), 
        sg.Radio('Binary', key='-BIN-', group_id='filetype'), 
        sg.Radio('.txt', key='-TXT-', group_id='filetype', default=True),
        sg.Text('Port:', pad=((210, 0), 0))
    ],

    [
        sg.Input(key='-FOLDER_PATH-', size=(50, 1)),
        sg.FolderBrowse(),
        sg.Combo(get_port_names(), key='-PORT-', size=(10, 1), pad=((47, 0), 0))
    ],

    [
        sg.Frame('Channels', ch_select_layout),
        sg.Column(column_layout, vertical_alignment='top')
    ],

    [
        sg.Multiline(key='-OUTPUT-', size=(79, 10), reroute_stdout=True, disabled=True)
    ]
]



window = sg.Window('Serial Monitor', layout)

measurment = 0    #broj mjerenja

# event loop
while True:


    event, values = window.read()

    if event == sg.WINDOW_CLOSED:
        break

    elif event == 'Start':

        window['-OUTPUT-'].update('') # clear output

        # get data from GUI and check for invalid inputs - empty fields, out of range values, etc.
        if not (values['-FOLDER_PATH-'] and values['-SAMPLES-'] and values['-ACQUISITIONS-']
                and values['-PORT-'] and values['-BOARD_REV-']):
            print('Error: All fields must be filled.')
            continue

        folder_path = values['-FOLDER_PATH-']
        port = values['-PORT-']
        samples = int(values['-SAMPLES-'])
        acquisitions = int(values['-ACQUISITIONS-'])
        board_rev = values['-BOARD_REV-']      #01/02

        channels_input = dict()
        for i in range(1, 9):
            channels_input[i] = values[f'ch{i}']
        channels = [ch for ch in channels_input if channels_input[ch]]

        if(not channels):
            print('Error: No channels selected.')
            continue

        if samples < 1 or samples > 3000:
            print('Error: Number of samples must be between 1 and 3000.')
            continue

        if acquisitions < 1 or acquisitions > 5000:
            print('Error: Number of acquisitions must be greater than 0.')
            continue

        if acquisitions < 1:
            print('Error: Multiple acquisitions are currently not supported. Work in progress.')
            continue

        if values['-BIN-']:
            print('Error: Binary files are currently not supported. Work in progress.')
            continue

        measurment = measurment + 1


        # get data from serial port
        print('Requesting {} samples from channels: {}\n'.format(samples, channels))
        data = serial_get_samples(port, samples, channels)

        if data:            
            print('Received:')
            for index, sample in enumerate(data):               
                print(index + 1, '. ', sample, sep='')         
            print()


            # TO DO: write to file(s)
            write_in_file(folder_path, board_rev, samples, acquisitions, channels, data)

            print('Logging finished:', time.strftime("%H:%M:%S", time.localtime()))

    # prevent user from typing in invalid values in samples and acquisitions fields
    elif event == '-SAMPLES-':
        validate_number_input('-SAMPLES-', window, values)

    elif event == '-ACQUISITIONS-':
        validate_number_input('-ACQUISITIONS-', window, values)

window.close()
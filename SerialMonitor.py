import PySimpleGUI as sg
import serial
import serial.tools.list_ports
import time
import datetime
import os.path
import os
import threading

sg.theme('Default 1')

# helper functions
def get_port_names():
    return [port.name for port in serial.tools.list_ports.comports()]

def validate_number_input(input_key, window, values):
    if len(values[input_key]) > 0 and values[input_key][-1] not in ('0123456789'):
            window[input_key].update(values[input_key][:-1])

def logging_time(file_name):
    now = datetime.datetime.now()
    return "Logging Finished: {}.{}.{} {:02d}:{:02d}:{:02d}\n"\
        .format(now.day, now.month, now.year, now.hour, now.minute, now.second)


def write_in_file(folder_path, board_rev, samples, measurement, channels, data):
    file_name = 'm_{:04d}.txt'.format(measurement)
    file_name = os.path.join(folder_path, file_name)

    try:
        with open(file_name, 'w') as file:
            file.write("#setup 0\n")
            file.write("#notes 3\n")
            file.write("Board revision: 01\n") if board_rev == 'Rev01' else file.write("Board revision: 02\n")
            file.write("Firmware Version: yy.mm.ab\n")  #verzija softvera?
            file.write(logging_time(file_name))
            file.write("#data {}, {}\n".format(samples, len(channels) + 1))
            file.write("sample, ")
            chlist = str()
            for i, _ in enumerate(channels):
                chlist += "ch{}, ".format(i + 1)
            file.write(f'{chlist[:-2]}\n')

            for index, _ in enumerate(data):               
                file.write("{}, ".format(index+1))
                row = str()
                for sample in data[index]:
                    row += "{}, ".format(sample)
                file.write(row[:-2] + "\n")
                
    except Exception as e:
        print('Error:', str(e))


def serial_get_samples(window, port_name, no_samples, channels):
    sp = serial.Serial(port_name, 9600)
    global data
    data = list()

    try:
        if not sp.isOpen():
            sp.open()

        data_to_send = no_samples.to_bytes(2, byteorder='little') + bytes(channels)
        sp.write(data_to_send)

        for _ in range(no_samples):
            sample = list()
            for _ in channels:
                sample.append(int.from_bytes(sp.read(2), byteorder='little'))
            data.append(sample)

    except Exception as e:
        print('Error:', str(e))

    finally:
        sp.close()
        window.write_event_value('-SAMPLING_FINISHED-', None)


def start_sampling():
    global thread
    thread = threading.Thread(target=serial_get_samples, args=(window, port, samples, channels))
    thread.start()

# layouts
ch_select_layout = [
    [sg.Checkbox(i, key=f'ch{i}', default=True) for i in range(1, 4)],
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
        sg.Input(key='-SAMPLES-', size=(15, 1), pad=((8, 20), 0), justification='center', enable_events=True, default_text='100'),
        sg.Input(key='-ACQUISITIONS-', size=(15, 1), pad=((0, 71), 0), justification='center', enable_events=True, default_text='1'),
        sg.Combo(['Rev01', 'Rev02'], key='-BOARD_REV-', size=(10, 1), default_value='Rev02')
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
        sg.Combo(get_port_names(), key='-PORT-', size=(10, 1), pad=((47, 0), 0), default_value=get_port_names()[-1])
    ],

    [
        sg.Frame('Channels', ch_select_layout),
        sg.Column(column_layout, vertical_alignment='top')
    ],

    [
        sg.Multiline(key='-OUTPUT-', size=(79, 15), reroute_stdout=True, disabled=True, autoscroll=True)
    ]
]

window = sg.Window('Serial Monitor', layout)

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

        global folder_path, port, samples, acquisitions, board_rev, channels

        folder_path = values['-FOLDER_PATH-']
        port = values['-PORT-']
        samples = int(values['-SAMPLES-'])
        acquisitions = int(values['-ACQUISITIONS-'])
        board_rev = values['-BOARD_REV-']

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
            print('Error: Number of acquisitions must be greater than 0 and less than 5000.')
            continue

        if values['-BIN-']:
            print('Error: Binary files are currently not supported. Work in progress.')
            continue

        # disable start button so the user can't start another acquisition before this one is finished
        window['Start'].update(disabled=True)
        
        # initialize global measurement counter
        global measurement
        measurement = 1

        print('Requesting {} samples from channels: {}\n'.format(samples, channels))
        start_sampling()    


    elif event == '-SAMPLING_FINISHED-':
        thread.join()

        if data:            
            write_in_file(folder_path, board_rev, samples, measurement, channels, data)
            
            print('Received (acquisition #{}):'.format(measurement))
            for index, sample in enumerate(data):               
                print(index + 1, '. ', sample, sep='')   

                if index % 50 == 0:
                    window.refresh()      
            print()

        # start another measurement if necessary
        if measurement < acquisitions:
            measurement += 1
            start_sampling()
        else:
            window['Start'].update(disabled=False)
            print('Logging finished:', time.strftime("%H:%M:%S", time.localtime()))



    # prevent user from typing in invalid values in samples and acquisitions fields
    elif event == '-SAMPLES-':
        validate_number_input('-SAMPLES-', window, values)

    elif event == '-ACQUISITIONS-':
        validate_number_input('-ACQUISITIONS-', window, values)

window.close()

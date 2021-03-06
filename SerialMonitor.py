import PySimpleGUI as sg
import serial
import serial.tools.list_ports
import time

sg.theme('Default 1')

# helper functions
def get_port_names():
    return [port.name for port in serial.tools.list_ports.comports()]
    
def validate_number_input(input_key, window, values):
    if len(values[input_key]) > 0 and values[input_key][-1] not in ('0123456789'):
            window[input_key].update(values[input_key][:-1])

def serial_get_samples(port_name, no_samples, channels):
    sp = serial.Serial(port_name, 9600)
    data_received = list()

    try:
        if sp.isOpen():
            sp.close()
        sp.open()

        data_to_send = [no_samples] + channels
        sp.write(bytes(data_to_send))

        for _ in range(no_samples):
            sample = list()
            for _ in channels:
                sample.append(int.from_bytes(sp.read(2), byteorder = 'little'))
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
        board_rev = values['-BOARD_REV-']

        channels_input = dict()
        for i in range(1, 9):
            channels_input[i] = values[f'ch{i}']
        channels = [ch for ch in channels_input if channels_input[ch]]

        if(not channels):
            print('Error: No channels selected.')
            continue

        if samples < 1 or samples > 255:
            print('Error: Number of samples must be 1-255.')
            continue
        
        if acquisitions < 1:
            print('Error: Number of acquisitions must be greater than 0.')
            continue

        if acquisitions > 1:
            print('Error: Multiple acquisitions are currently not supported. Work in progress.')
            continue

        if values['-BIN-']:
            print('Error: Binary files are currently not supported. Work in progress.')
            continue


        # get data from serial port
        print('Requesting {} samples from channels: {}\n'.format(samples, channels))
        data = serial_get_samples(port, samples, channels)
        
        if data:
            print('Received:')
            for index, sample in enumerate(data):
                print(index + 1, '. ', sample, sep='')
            print()


            # TO DO: write to file(s)


            print('Logging finished:', time.strftime("%H:%M:%S", time.localtime()))
    
    # prevent user from typing in invalid values in samples and acquisitions fields
    elif event == '-SAMPLES-':
        validate_number_input('-SAMPLES-', window, values)

    elif event == '-ACQUISITIONS-':
        validate_number_input('-ACQUISITIONS-', window, values)

window.close()


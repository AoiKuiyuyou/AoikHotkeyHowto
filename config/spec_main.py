# coding: utf-8
"""
This module contains hotkey spec list.
"""
from __future__ import absolute_import

# Standard imports
from contextlib import contextmanager
from functools import partial
from functools import wraps
from os.path import os
from os.path import splitdrive
import pathlib
import re
import sys
import time
import webbrowser

# Internal imports
from aoikhotkey.const import SPEC_SWITCH_V_NEXT
from aoikhotkey.const import SPEC_SWITCH_V_PREV
from aoikhotkey.util.cmd import Cmd
from aoikhotkey.util.cmd import Quit
from aoikhotkey.util.cmd import Sleep
from aoikhotkey.util.cmd import SpecReload
from aoikhotkey.util.cmd import SpecSwitch
from aoikhotkey.util.efunc import efunc_no_mouse
from aoikhotkey.util.keyboard_winos import SendKeys
from aoikhotkey.util.keyboard_winos import SendSubs

# External imports
import pywinauto
from win32clipboard import CloseClipboard
from win32clipboard import EmptyClipboard
from win32clipboard import GetClipboardData
from win32clipboard import OpenClipboard
from win32clipboard import SetClipboardText
from win32con import CF_TEXT
from win32con import CF_UNICODETEXT
import win32gui
from win32ui import GetForegroundWindow
import zbase62.zbase62 as zbase62


try:
    # Python 3
    from urllib.parse import quote
except ImportError:
    # Python 2
    from urllib import quote

try:
    # Python 3
    from urllib.parse import urlsplit
except ImportError:
    # Python 2
    from urlparse import urlsplit

try:
    # Python 3
    from urllib.parse import unquote_plus
except ImportError:
    # Python 2
    from urllib import unquote_plus


# Whether is Python 2
_IS_PY2 = (sys.version_info[0] == 2)


def Edit(path):
    """
    Create hotkey function that opens editor for given path.

    :param path: Path of the file to open in editor.

    :return: `Cmd` object.
    """
    # Create hotkey function
    return Cmd(
        r'D:\Software\Dev\IDE\SublimeText\0\dst\sublime_text.exe',
        path,
    )


def close_foreground_program():
    """
    Close foreground program.

    :return: None.
    """
    # Get foreground window handle
    fg_hwnd = GetForegroundWindow().GetSafeHwnd()

    # Get pywinauto window object
    window = pywinauto.application.Application().window_(handle=fg_hwnd)

    # Get window title
    window_title = win32gui.GetWindowText(win32gui.GetForegroundWindow())

    # If window class is `ConsoleWindowClass`
    if window.Class() == 'ConsoleWindowClass':
        #
        if 'aoikhotkey' in window_title.lower():
            # Print message
            print('Ignore window title with `aoikhotkey`')

            # Return
            return

        # Use "pywinauto" to close because "ConsoleWindowClass" do not respond
        # to "Alt+F4".
        window.Close()
    # If window class is not `ConsoleWindowClass`
    else:
        # If the window title contains `VNC Viewer`
        if 'VNC Viewer' in window_title:
            # Send keys
            SendKeys('#q')()

            # Return
            return

        # If the window title contains `Sublime Text`
        if 'Sublime Text' in window_title:
            # Print message
            print('Ignore window title with `Sublime Text`')

            # Return
            return

        # Close the window
        window.Close()


@contextmanager
def clipboard_preserve_context():
    """
    Preserve clipboard value on entering the context, and restore on exiting.

    :return: None.
    """
    try:
        # Get current value in clipboard
        text_old = clipboard_get_text()
        # ^ raise error
    except Exception:
        # Use None as current value in case of error
        text_old = None

    # End of entering-context code
    yield text_old

    # Start of exiting-context code

    # If clipboard had text
    if text_old is not None:
        # Set clipboard to old text
        try:
            # Open clipboard
            clipboard_open()

            # Empty clipboard
            EmptyClipboard()

            # Set old text to clipboard
            SetClipboardText(text_old, CF_TEXT)

            # Set old text to clipboard as Unicode
            SetClipboardText(text_old, CF_UNICODETEXT)
        except Exception:
            # Ignore any error
            pass
        finally:
            # Close clipboard
            CloseClipboard()


def clipboard_preserve_decorator(func):
    """
    Call the wrapped function in a "clipboard_preserve_context".

    :param func: the wrapped function.

    :return: the wrapping function.
    """
    # Define a wrapping function
    @wraps(func)
    def new_func(*args, **kwargs):
        # Call the function in the context
        with clipboard_preserve_context():
            # Call the function
            return func(*args, **kwargs)

    # Return the wrapping function
    return new_func


def clipboard_open(try_times=10):
    """
    Open clipboard.

    :param try_times: number of times to try in case of error.

    :return: None.
    """
    # Tried times
    tried_times = 0

    while True:
        # Increment tried times
        tried_times += 1

        try:
            # Open clipboard
            OpenClipboard()

            # Get out of the try loop
            break
        except Exception:
            # If tried enough times
            if tried_times >= try_times:
                # Raise error
                raise
            else:
                # Sleep to keep from being too fast
                time.sleep(0.1)

                # Re-try
                continue


def clipboard_get_text(to_open=True, to_close=True):
    """
    Get text from clipboard.

    :param to_open: open clipboard before doing.

    :param to_close: close clipboard after done.

    :return: the text.
    """
    # If need open clipboard
    if to_open:
        # Open clipboard
        clipboard_open()

    try:
        # Get text from clipboard
        text = GetClipboardData(CF_TEXT)

        # Return the text
        return text
    finally:
        # If need close clipboard
        if to_close:
            # Close clipboard
            CloseClipboard()


def clipboard_set_text(text, to_open=True, to_close=True):
    """
    Set text to clipboard.

    :param text: the text to set.

    :param to_open: open clipboard before doing.

    :param to_close: close clipboard after done.

    :return: None.
    """
    # If need open clipboard
    if to_open:
        # Open clipboard
        OpenClipboard()

    #
    try:
        # Empty clipboard
        EmptyClipboard()

        # Set text to clipboard
        SetClipboardText(text, CF_TEXT)

        # Set text to clipboard as Unicode
        SetClipboardText(text, CF_UNICODETEXT)
    finally:
        # If need close clipboard
        if to_close:
            # Close clipboard
            CloseClipboard()


@clipboard_preserve_decorator
def paste_text(text):
    """
    Set text to clipboard and paste.

    :param text: the text to paste.

    :return: None.
    """
    # Set text to clipboard
    clipboard_set_text(text)

    # Sleep
    time.sleep(0.05)

    # Send "Ctrl+v" to paste
    SendKeys('^v')()


def base62_text_is_ok(text):
    """
    Check if the text is ok to use.

    :param text: the text to check.

    :return: Boolean.
    """
    # Get the first character
    char_first = text[0]

    # If the first character is a digit and is not "0"
    if char_first.isdigit() and char_first != '0':
        # Return True
        return True
    else:
        # Return False
        return False


def base62_text_gen(text_length=None, try_times=100):
    """
    Generate a random sequence of bytes, encode it in base62.

    :param try_times: number of times to try.

    :return: the base62-encoded text.
    """
    # Tried times
    tried_times = 0

    # Start to generate
    while True:
        # Increment tried times
        tried_times += 1

        # If have tried enough times
        if tried_times > try_times:
            # Raise error
            raise ValueError('Tried {} times'.format(try_times))

        # Generate random bytes
        byte_s = os.urandom(16)

        # Encode the random bytes using base62
        text = zbase62.b2a(byte_s)

        # If "text_length" is given
        if text_length is not None:
            # Limit to the length
            text = text[0:text_length]

        # Convert to uppercase
        text = text.upper()

        # If the text is ok to use
        if base62_text_is_ok(text):
            # Return
            return text
        # If the text is not ok to use
        else:
            # Re-generate in the next loop
            continue


@clipboard_preserve_decorator
def id_generate_paste():
    """
    Generate a random base62-encoded text, set it to clipboard and paste.

    :return: None.
    """
    # Generate ID text
    id_text = base62_text_gen(text_length=5)

    # Set to clipboard
    clipboard_set_text(id_text)

    # Send "Ctrl+v" to paste
    SendKeys('^v')()

    # Sleep to keep from being too fast
    time.sleep(0.03)


def transform_special_chars(text):
    """
    Transform text so that it is suitable as file name.

    :param text: the text to transform.

    :return: the transformed text.
    """
    # Replace "/" with "--".
    # E.g. "pypi.python.org/pypi" becomes "pypi.python.org--pypi".
    text = text.replace('/', '--')

    # Transform special characters
    text_quoted = quote(text, safe="!#$%&'()*+,-.;=@[]^_`{}~ ")

    # Return the transformed text
    return text_quoted


def transform_file_path(path):
    """
    Transform a file path until it is not existing, by adding incremented
    number postfix. E.g. "pypi.python.org.url" becomes "pypi.python.org_2.url"

    :param path: the path to transform.

    :return: the transformed path.
    """
    # Split the path
    path_noext, ext = os.path.splitext(path)

    # The new path
    new_path = path

    # The postfix number
    postfix_number = 1

    # If the new path exists
    while os.path.exists(new_path):
        # Increment the postfix number
        postfix_number += 1

        # Create a new path
        new_path = '{}_{}{}'.format(path_noext, postfix_number, ext)

        # Try the new path in the next loop
        continue

    # Return the transformed path.
    return new_path


def create_url_file(url, output_dir):
    """
    Create a `.url` file.

    :param url: the URL value.

    :param output_dir: the output directory path.

    :return: None.
    """
    # Handle no scheme case.
    # E.g. Call "urlsplit" with "pypi.python.org/" returns
    # SplitResult(
    #   scheme='',
    #   netloc='',
    #   path='pypi.python.org/',
    #   query='',
    #   fragment=''
    # )
    # due to the missing scheme "http://".

    # Split the url
    part_s = urlsplit(url)

    # Get scheme part
    scheme = part_s[0]

    # If no scheme
    if not scheme:
        # Add scheme
        url = 'http://' + url

        # Split the url again
        part_s = urlsplit(url)

    # Ensure scheme is existing
    assert part_s[0]

    # Get netloc part
    netloc = part_s[1]

    # Get path part
    path = part_s[2]

    # Get file name
    url_file_name = netloc + path

    # Transform special characters
    url_file_name = transform_special_chars(url_file_name)

    # Get query part
    query = part_s.query

    # If has query part
    if query:
        # Transform special characters
        query = transform_special_chars(query)

        # Add query part to file name.
        # Use "@" to replace "?".
        url_file_name = '{}@{}'.format(url_file_name, query)

    # Get fragment part
    fragment = part_s.fragment

    # If has fragment part
    if fragment:
        # Transform special characters
        fragment = transform_special_chars(fragment)

        # Add fragment part to file name.
        url_file_name = '{}#{}'.format(url_file_name, fragment)

    # Strip ending "-"
    url_file_name = url_file_name.rstrip('-')

    # Add trailing space
    url_file_name_no_ext_with_space = url_file_name + ' '

    # Add ".url" file extension
    url_file_name = url_file_name + '.url'

    # Make a file path using the output directory
    url_file_path = os.path.join(output_dir, url_file_name)

    # If the file path is existing
    if os.path.exists(url_file_path):
        # Touch the existing file instead of creating new file
        pathlib.Path(url_file_path).touch()

        # Return
        return

    # Get output directory's existing file names
    output_dir_file_name_s = os.listdir(output_dir)

    # For each existing file name
    for output_dir_file_name in output_dir_file_name_s:
        # If the existing file name starts with the URL file name plus space
        if output_dir_file_name.startswith(url_file_name_no_ext_with_space):
            # Use the existing file path
            output_dir_file_path = os.path.join(
                output_dir, output_dir_file_name
            )

            # Touch the existing file instead of creating new file
            pathlib.Path(output_dir_file_path).touch()

            # Return
            return

    # Store escaped file path
    escaped_url_file_path = url_file_path

    # Convert to unescaped file path
    url_file_path = unquote_plus(url_file_path)

    # If is Python 2
    if _IS_PY2:
        # Convert bytes to Unicode
        url_file_path = url_file_path.decode('gbk')

    # Transform the file path until it is not existing
    url_file_path = transform_file_path(url_file_path)

    # File path length limit
    len_max = 200

    # If exceeded the file path length limit
    if len(url_file_path) > len_max:
        # Print message
        print('Warning: File name is too long.')

        # Truncate the file path
        url_file_path = url_file_path[:len_max] + '.url'

        # Transform the file path
        url_file_path = transform_file_path(url_file_path)

    #
    try:
        # Open output file
        file = open(url_file_path, mode='w')
    except Exception:
        # Get escaped url file path
        url_file_path = escaped_url_file_path[:len_max] + '.url'

        # Open output file
        file = open(url_file_path, mode='w')

    # Create ".url" file content
    url_file_content = '[InternetShortcut]\nURL={}'.format(url)

    # Open output file
    with file as file:
        # Write content to file
        file.write(url_file_content)


def send_keys_to_copy():
    # Send "Ctrl+c" to copy the URL in location bar
    SendKeys(r'<^c')()

    # Sleep to keep from being too fast
    time.sleep(0.05)


def send_keys_to_copy_location_bar_text():
    # Send "Ctrl+l" to move focus to location bar
    SendKeys(r'<^l')()

    # Sleep to keep from being too fast
    time.sleep(0.05)

    # Send "Ctrl+c" to copy the URL in location bar
    SendKeys(r'<^c')()

    # Sleep to keep from being too fast
    time.sleep(0.05)


@clipboard_preserve_decorator
def browser_url_save():
    """
    Read URL from a browser's location bar, save as a `.url` file.

    :return: None.
    """
    #
    send_keys_to_copy_location_bar_text()

    # Get the url from clipboard
    text = clipboard_get_text()

    # If is not Python 2
    if not _IS_PY2:
        # Convert text to Unicode
        text = text.decode('gbk')

    # Move focus off the location bar
    SendKeys('{LAlt}')()

    # Create ".url" file
    create_url_file(url=text, output_dir=r'D:\SoftwareData\URL')


@clipboard_preserve_decorator
def open_parallel_dir(base_dir, create=False):
    """
    Open parallel directory of the current directory in Windows Explorer.
    E.g. jump from "D:\Study\Dev\Lang\Python" to "D:\Software\Dev\Lang\Python".

    :param base_dir: the base directory of the destination directory.

    :param create: create if the destination directory is not existing.

    :return: None.
    """
    # Send "Ctrl+l" to move focus to location bar
    SendKeys(r'<^l')()

    # Sleep to keep from being too fast
    time.sleep(0.05)

    # Send "Ctrl+c" to copy the current directory path
    SendKeys(r'<^c')()

    # Sleep to keep from being too fast
    time.sleep(0.05)

    # Get the current directory path from clipboard
    dir_path_in_bar = clipboard_get_text()

    # If current directory is empty
    if not dir_path_in_bar:
        # Exit
        return

    # If is not Python 2
    if not _IS_PY2:
        # Convert to Unicode
        dir_path_in_bar = dir_path_in_bar.decode('gbk')

    # Remove the "drive" part from the directory path.
    # E.g. "D:\Study" becomes "\Study"
    _, dir_path = splitdrive(dir_path_in_bar)

    # Print message
    print('Origin: {}'.format(dir_path))

    # Strip slashes
    dir_path = dir_path.strip('\\/')

    # Whether the current directory path starts with any of the prefixes below
    start_with_prefix = False

    # Start to find a matching prefix
    for prefix in [
        'Study',
        'Software',
        'SoftwareData',
        'All\\Software2\\SoftwareBig',
        'All\\Software2\\SoftwareSmall',
    ]:
        # If the current directory path starts with the prefix
        if (dir_path + '\\').startswith(prefix + '\\'):
            # Set the boolean
            start_with_prefix = True

            # Remove the prefix
            rel_path = dir_path[len(prefix):]

            # Left-strip slashes
            rel_path = rel_path.lstrip('\\/')

            # Create a new directory path
            dir_path_new = os.path.join(base_dir, rel_path)

            # Replace backslash with forward slash
            dir_path_new = dir_path_new.replace('\\', '/')

            # If to create a destination path if it is not existing
            if create:
                # If the destination path is not existing
                if not os.path.isdir(dir_path_new):
                    # Create destination path
                    os.makedirs(dir_path_new)

                # Message
                print('Open: {}'.format(dir_path_new))

                # Open the destination path
                webbrowser.open(dir_path_new)

                # Exit
                return
            # If not to create a destination path if it is not existing
            else:
                # Start to find the closest upper directory
                while True:
                    # If the destination path is existing
                    if os.path.isdir(dir_path_new):
                        # Message
                        print('Open: {}'.format(dir_path_new))

                        # Open the destination path
                        webbrowser.open(dir_path_new)

                        # Exit
                        return
                    # If the destination path is not existing
                    else:
                        # Get the parent directory
                        dir_path_new = os.path.dirname(dir_path_new)

                        # Remove the "drive" part
                        path_part = os.path.splitdrive(dir_path_new)[1]

                        # If the parent directory is partition root
                        if path_part in ('', '/', '\\'):
                            # Message
                            print('Ignore: {}'.format(dir_path_in_bar))

                            # Exit
                            return
                        else:
                            # Try the parent directory in the next loop
                            continue

    # If the current directory path not starts with the any of the prefixes
    if not start_with_prefix:
        # Message
        print('Open: {}'.format(base_dir))

        # Open the base destination directory
        webbrowser.open(base_dir)

        # Exit
        return


def open_clipboard_url_in_browser():
    """
    Hotkey function that gets URL from clipboard and opens in browser.

    :return: None.
    """
    # Get URL from clipboard
    url = clipboard_get_text()

    # If is not Python 2
    if not _IS_PY2:
        # Convert the text to Unicode
        url = url.decode('gbk')

    # If the URL is not empty
    if url:
        # If the URL is existing file path
        if os.path.exists(url):
            # Open in file explorer
            webbrowser.open(url)

        # If the URL is not existing file path,
        # it is assumed to be URL.
        else:
            # If the URL starts with any of these prefixes
            if url.startswith('http://') \
                    or url.startswith('https://') \
                    or url.startswith('www.'):
                # Open the URL in browser
                webbrowser.open(url)


def copy_url_open_in_browser():
    """
    Hotkey function that copies URL to clipboard and opens the URL in browser.

    :return: None.
    """
    # Copy URL to clipboard
    send_keys_to_copy()

    # Open the copied URL in browser
    open_clipboard_url_in_browser()


def clipboard_to_lowercase():
    """
    Hotkey function that converts text in clipboard to uppercase.

    :return: None.
    """
    # Open clipboard
    clipboard_open()

    try:
        # Get text from clipboard
        text = GetClipboardData(CF_TEXT)

        # If the text is empty
        if not text:
            # Ignore
            return

        # Convert to lower case
        text = text.lower()

        # Empty clipboard
        EmptyClipboard()

        # Set text to clipboard
        SetClipboardText(text, CF_TEXT)

        # If is not Python 2
        if not _IS_PY2:
            # Convert the text to Unicode
            text = text.decode('gbk')

        # Set text to clipboard as Unicode
        SetClipboardText(text, CF_UNICODETEXT)
    finally:
        # Close clipboard
        CloseClipboard()


def clipboard_to_uppercase():
    """
    Hotkey function that converts text in clipboard to UPPERCASE.

    :return: None.
    """
    # Open clipboard
    clipboard_open()

    try:
        # Get text from clipboard
        text = GetClipboardData(CF_TEXT)

        # If the text is empty
        if not text:
            # Ignore
            return

        # Convert to upper case
        text = text.upper()

        # Empty clipboard
        EmptyClipboard()

        # Set text to clipboard
        SetClipboardText(text, CF_TEXT)

        # If is not Python 2
        if not _IS_PY2:
            # Convert the text to Unicode
            text = text.decode('gbk')

        # Set text to clipboard as Unicode
        SetClipboardText(text, CF_UNICODETEXT)
    finally:
        # Close clipboard
        CloseClipboard()


def clipboard_to_pascalcase():
    """
    Hotkey function that converts text in clipboard to PascalCase.

    :return: None.
    """
    # Open clipboard
    clipboard_open()

    try:
        # Get text from clipboard
        text = GetClipboardData(CF_TEXT)

        # If the text is empty
        if not text:
            # Ignore
            return

        # If is not Python 2
        if not _IS_PY2:
            # Convert the text to Unicode
            text = text.decode('gbk')

        # Replace non-letter character to space
        text = re.sub(r'[^A-Z0-9a-z]', ' ', text)

        # Split text to words by white-space,
        # capitalize each word,
        # join the capitalized words into text.
        text = ''.join(word.capitalize() for word in text.split())

        # Empty clipboard
        EmptyClipboard()

        # Set text to clipboard
        SetClipboardText(text, CF_TEXT)

        # Set text to clipboard as Unicode
        SetClipboardText(text, CF_UNICODETEXT)
    finally:
        # Close clipboard
        CloseClipboard()


def clipboard_to_camelcase():
    """
    Hotkey function that converts text in clipboard to camelCase.

    :return: None.
    """
    # Open clipboard
    clipboard_open()

    try:
        # Get text from clipboard
        text = GetClipboardData(CF_TEXT)

        # If the text is empty
        if not text:
            # Ignore
            return

        # If is not Python 2
        if not _IS_PY2:
            # Convert the text to Unicode
            text = text.decode('gbk')

        # Replace non-letter character to space
        text = re.sub(r'[^A-Z0-9a-z]', ' ', text)

        # Split text to words by white-space,
        # capitalize each word,
        # join the capitalized words into text.
        text = ''.join(word.capitalize() for word in text.split())

        # If the text is not empty
        if text:
            # Convert the text to camelCase
            text = text[0].lower() + text[1:]

        # Empty clipboard
        EmptyClipboard()

        # Set the text to clipboard
        SetClipboardText(text, CF_TEXT)

        # Set text to clipboard as Unicode
        SetClipboardText(text, CF_UNICODETEXT)
    finally:
        # Close clipboard
        CloseClipboard()


def send_copy_hotkey():
    """
    Hotkey function that sends keys for copying.

    :return: None.
    """
    # Get window title
    window_title = win32gui.GetWindowText(win32gui.GetForegroundWindow())

    # If the window title contains `VNC Viewer`
    if 'VNC Viewer' in window_title:
        # Send keys
        SendKeys(r'#c')()
    else:
        # Send keys
        SendKeys(r'^{Insert}')()


def send_paste_hotkey():
    """
    Hotkey function that sends keys for pasting.

    :return: None.
    """
    # Get window title
    window_title = win32gui.GetWindowText(win32gui.GetForegroundWindow())

    # If the window title contains `VNC Viewer`
    if 'VNC Viewer' in window_title:
        # Send keys
        SendKeys(r'#v')()
    else:
        # Send keys
        SendKeys(r'+{Insert}')()


def open_editor():
    """
    Hotkey function that opens editor.

    :return: None.
    """
    # Get window title
    window_title = win32gui.GetWindowText(win32gui.GetForegroundWindow())

    # If the window title contains `VNC Viewer`
    if 'VNC Viewer' in window_title:
        # Propagate the event
        return True
    else:
        # Open editor
        Cmd(r'D:\Software\Dev\IDE\SublimeText\0\dst\sublime_text.exe')()


SPEC = [
    # ----- Event function -----

    # None means event function
    (None, efunc_no_mouse),

    # ----- ESC -----

    ('#+{ESC}', 'B:/'),

    # Reload hotkey spec
    ('+{ESC}', SpecReload),

    ('!{ESC}', partial(open_parallel_dir, base_dir=r'D:/Study')),

    ('#!{ESC}', partial(open_parallel_dir, base_dir=r'D:/Study', create=True)),

    ('::{ESC}1', partial(paste_text, r"""SELECT *
FROM
WHERE 1
AND 1
ORDER BY id DESC
LIMIT 10
""")),

    ('::{ESC}2', partial(paste_text, r"""SHOW CREATE TABLE """)),

    ('::{ESC}7', partial(paste_text, r"""#
select *
from (
    # Global Priv
    select user, host, '*' as db, '*' as tb,
    if(select_priv='Y', '*.*', '') AS 'SELECT',
    if(insert_priv='Y', '*.*', '') AS 'INSERT',
    if(update_priv='Y', '*.*', '') AS 'UPDATE',
    if(delete_priv='Y', '*.*', '') AS 'DELETE',
    if(create_priv='Y', '*.*', '') AS 'CREATE',
    if(drop_priv='Y', '*.*', '') AS 'DROP',
    if(index_priv='Y', '*.*', '') AS 'INDEX',
    if(alter_priv='Y', '*.*', '') AS 'ALTER'
    from mysql.user
    UNION
    # Database Priv
    select user, host, db, '' as tb,
    if(select_priv='Y', CONCAT(db, '.*'), ''),
    if(insert_priv='Y', CONCAT(db, '.*'), ''),
    if(update_priv='Y', CONCAT(db, '.*'), ''),
    if(delete_priv='Y', CONCAT(db, '.*'), ''),
    if(create_priv='Y', CONCAT(db, '.*'), ''),
    if(drop_priv='Y', CONCAT(db, '.*'), ''),
    if(index_priv='Y', CONCAT(db, '.*'), ''),
    if(alter_priv='Y', CONCAT(db, '.*'), '')
    from mysql.db
    UNION
    # Table Priv
    select user, host, db, table_name,
    if(table_priv & 1, 'Table', ''),
    if(table_priv & 2, 'Table', ''),
    if(table_priv & 4, 'Table', ''),
    if(table_priv & 8, 'Table', ''),
    if(table_priv & 16, 'Table', ''),
    if(table_priv & 32, 'Table', ''),
    if(table_priv & 256, 'Table', ''),
    if(table_priv & 512, 'Table', '')
    from mysql.tables_priv
) as t1
where 1
order by user, host, db, tb
#where user = '_user_'
""")),

    ('::{ESC}8', partial(paste_text, r"""SELECT `AUTO_INCREMENT`
FROM  INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = '_DB_'
AND   TABLE_NAME   = '_TABLE_';
""")),

    ('::{ESC}9', partial(
        paste_text, r"""ALTER TABLE _TABLE_ AUTO_INCREMENT = 1;"""
    )),

    # ----- F1 -----
    # Reserve: ^F1 -> Sublime Text `toggle comment`

    ('F1', 'https://www.google.com/'),

    ('+F1',
        SendKeys('^c'),
        Sleep(0.02),
        clipboard_to_lowercase,
        SendKeys('^v')),

    ('#+F1', 'C:/'),

    ('!F1', partial(open_parallel_dir, base_dir=r'D:/Software')),

    ('#!F1', partial(open_parallel_dir, base_dir=r'D:/Software', create=True)),

    # ----- F2 -----
    # Reserve: ^F2 -> Goto paired bracket (Sublime Text)

    ('F2', 'http://global.bing.com/?setmkt=en-us&setlang=en-us'),

    ('#+F2', 'D:/'),

    ('+F2',
        SendKeys('^c'),
        Sleep(0.02),
        clipboard_to_uppercase,
        SendKeys('^v')),

    ('!F2', partial(
        open_parallel_dir, base_dir=r'F:/all/Software2/SoftwareSmall'
    )),

    ('#!F2', partial(
        open_parallel_dir,
        base_dir=r'F:/all/Software2/SoftwareSmall', create=True
    )),

    # ----- F3 -----
    # Reserve: ^+F3: Select content inside brackets (Sublime Text)

    ('F3', 'http://fanyi.youdao.com/'),

    ('+F3',
        SendKeys('^c'),
        Sleep(0.02),
        clipboard_to_pascalcase,
        SendKeys('^v')),

    ('#+F3', 'E:/'),

    ('!F3', partial(
        open_parallel_dir, base_dir=r'F:/all/Software2/SoftwareBig')),

    ('#!F3', partial(
        open_parallel_dir,
        base_dir=r'F:/all/Software2/SoftwareBig', create=True
    )),

    # ----- F4 -----

    ('F4', 'http://www.sogou.com/'),

    ('+F4',
        SendKeys('^c'),
        Sleep(0.02),
        clipboard_to_camelcase,
        SendKeys('^v')),

    ('#+F4', 'F:/'),

    # ----- F5 -----

    ('!F5', partial(open_parallel_dir, base_dir=r'D:/SoftwareData')),

    ('#!F5', partial(
        open_parallel_dir, base_dir=r'D:/SoftwareData', create=True
    )),

    ('#+F5', 'G:/'),

    # ----- F6 -----

    # ----- F7 -----

    # ----- F8 -----

    # ----- F9 -----

    ('F9', Edit(
        r'D:\SoftwareData\FileTypeAsso\AoikWinFileTypeAsso\config.yaml'
    )),

    # ----- F10 -----

    # ----- F11 -----
    # Reserve: F11 -> Full screen

    # ----- F12 -----

    ('F12', 'http://127.0.0.1:8000/'),

    # ----- 1 -----

    ('^1', browser_url_save),

    ('!1', r'D:\Study\Dev\Lang'),

    ('::`12', SendSubs('127.0.0.1')),

    # ----- 2 -----

    ('^2', SendKeys('^w')),

    ('!2', r'D:\SoftwareData\Dev\Proj'),

    # ----- 3 -----

    ('$^3', id_generate_paste),

    # ----- 4 -----
    # Reserve: ^4 -> Sublime Text `tidy_by_context`

    ('#4', r'D:\Software\Net\SSH\WinSCP\0\dst\WinSCP.exe'),

    ('!4', r'D:\Study\Dev\Lang\JavaScript'),

    # ----- 5 -----

    ('!5', r'D:\Study\Dev\Lang\Ruby'),

    # ----- 6 -----

    # ----- 7 -----

    ('!7', Edit(r'C:\Windows\System32\drivers\etc\hosts')),

    # ----- 8 -----

    # ----- 9 -----

    # ----- 0 -----

    # ----- a -----
    # Reserve: ^a -> Select all

    ('#a', r'E:\all'),

    ('!a', r'D:\Study'),

    # ----- b -----
    # Reserve: ^b -> Build (Sublime Text)
    # Reserve: ^+b -> Build with selection (Sublime Text)

    ('!b', r'D:\Study\Dev\Database'),

    ('#b',
        r'D:\Software\Dev\Database\SQL\MySQL\Client\SQLyog\0\dst\SQLyog.exe'),

    # ----- c -----
    # Reserve: ^+c -> Chrome Developer tools

    ('<!c', r'D:\SoftwareCMD'),

    # Use Ctrl+Insert to copy.
    # It works better in console programs like Putty.
    (
        '^c',
        send_copy_hotkey,
    ),

    ('#c', r'D:\Study\Dev\Lang\_Comparison'),

    # ----- d -----
    # Reserve: ^d -> Delete
    # Reserve: ^+d -> Sublime Text `duplicate_line`

    ('^!d', r'D:\Study\Dev'),

    ('#d', r'C:\Users\Aoik\Downloads'),

    ('!d', r'E:\Download'),

    # ----- e -----

    ('$^e', open_editor),

    ('#e', r'D:\Software\Dev\IDE\Notepad++\0\dst\notepad++.exe'),

    ('^+e', 'D:\Software\Dev\IDE\Emacs\emacs.bat'),

    ('^#e', r'D:\Software\Dev\IDE\Vim\0\dst\gvim.exe'),

    ('^!e', Edit(
        (
            r'D:\Study\Util\Hotkey\AoikHotkey\Config\aoikhotkeyconfig'
            r'\spec_main.py'
        )
    )),

    # ----- f -----
    # Reserve: ^f -> Find. In Eclipse means Find/Replace.
    # Reserve: ^+f -> Find Globally.
    # Reserve: ^!f -> Find reversely.

    # ----- g -----
    # Reserve: ^g -> Goto

    ('!+g', r'D:\Study\Dev\Lang\Go'),

    # ----- h -----
    # Reserve: ^h -> Replace
    # Reserve: ^h -> Find/Replace Globally (Eclipse)
    # Reserve: ^+h -> Replace Globally (Netbeans)

    ('#h', r'C:\Users\Aoik'),

    ('!h', r'D:\Study\Dev\Lang\JavaScript\Net\HTML+CSS'),

    ('!+h', r'D:\Study\Util\Hotkey'),

    # ----- i -----
    # Reserve: ^+i -> Netbeans organize imports
    # Reserve: ^+i -> Chrome Developer tools

    ('<^i', Cmd(
        (
            r'D:\Software\Util\Registry\AezayRegistryCommander\0\dst'
            r'\RegCmd.exe')
    )),

    ('>^i', 'regedit.exe'),

    # ----- j -----
    # Reserve: ^j -> Sublime Text `join_lines`

    # ----- k -----
    # Reserve: ^k -> Emacs style prefix character

    ('^!k', r'D:\Software\A.V.I\Player\PotPlayer\0\dst\PotPlayerMini64.exe'),

    # ----- l -----

    ('^l', Cmd(
        'hstart', r'cmd /K polipo_v2.bat'
    )),

    ('!l', r'D:\Software\Language'),

    # ----- m -----

    ('!+m', r'D:\Study\OS\Mac\MacOS'),

    # ----- n -----
    # Reserve: ^n -> New File
    # Reserve: ^+n -> New Window

    ('#n', r'ncpa.cpl'),

    ('<!n', r'D:\Study\Net'),

    ('>!n', r'D:\Software\Net'),

    # ----- o -----
    # Reserve: ^+o -> Eclipse organize imports

    # ----- p -----

    ('<^p', Cmd('hstart', r'cmd /C python3.bat')),

    ('>^p', Cmd('hstart', r'cmd /C python2.bat')),

    ('<^!p', r'D:\Software\Dev\Lang\Python\3\dst\Lib\site-packages'),

    ('>^!p', r'D:\Software\Dev\Lang\Python\2\dst\Lib\site-packages'),

    ('>#p', r'appwiz.cpl'),

    ('!p', r'D:\Study\Dev\Lang\Python'),

    ('<#p', r'D:\Software\Dev\Lang\Python'),

    # ----- q -----
    # Reserve: !q -> Reserved for Sublime Text `Open containing folder`

    ('^q', close_foreground_program),

    ('^!q', r'D:\Software\Net\IM\QQ\0\dst\Bin\QQ.exe'),

    ('^!+q', Quit),

    # ----- r -----
    # Reserve: ^r -> Replace
    # Reserve: ^+r -> Find symbol (Atom, Sublime Text)
    # Reserve: #r -> Run (Windows)

    ('!r', copy_url_open_in_browser),

    # ----- s -----
    # Reserve: ^s -> Save

    ('#s', r'services.msc'),

    ('!s', r'D:\Software'),

    # ----- t -----
    # Reserve: ^t -> Open terminal (OS X Spark Hotkey Manager)
    # Reserve: ^+t -> Reopen last tab

    ('#t', r'D:\Software\Net\SSH\Putty\0\dst\PuTTYPortable.exe'),

    # ----- u -----
    ('!+u', r'D:\Study\Dev\UI'),

    # ----- v -----

    # Use "Shift+Insert" to paste.
    # It works better in console programs like Putty.
    (
        '^v',
        send_paste_hotkey,
    ),

    # ----- w -----
    # Reserve: ^w -> Close tab

    ('^!w', r'D:\Software\A.V.I\Player\foobar2000\0\dst\foobar2000.exe'),

    ('!w', r'D:\SoftwareData\URL'),

    ('!+w', r'D:\Study\OS\Windows'),

    ('#!w', r'D:\SoftwareData\URL_Old'),

    # ----- x -----
    # Reserve: ^x -> Cut

    # ----- y -----
    # Reserve: ^y -> Redo

    ('#y', r'D:\Software\Net\Download\Thunder\0\dst\Program\Thunder.exe'),

    # ----- z -----
    # Reserve: ^z -> Undo

    ('^!z', r'D:\SoftwareCMD\cmd_runasadmin.lnk'),

    ('!z', Cmd('hstart', r'cmd /K D:\SoftwareCMD\clink_v2.bat')),

    # ----- ` -----

    ('^`', SendKeys('^!{Left}')),

    ('#`', SendKeys('^!{Right}')),

    ('^!`', r'D:\Software\Util\Wox\0\dst\Wox.exe'),

    ('^#`', Cmd(
        r'D:\Software\Util\ProcessUtil\ProcessExplorer\0\dst\procexp.exe'
    )),

    # ----- - -----

    # ----- = -----

    ('^=', r'diskmgmt.msc'),

    # ----- [ -----

    ('^![', SpecSwitch(SPEC_SWITCH_V_PREV)),

    # ----- ] -----

    ('^!]', SpecSwitch(SPEC_SWITCH_V_NEXT)),

    # ----- \ -----

    # ----- ; -----

    # ----- ' -----

    # ----- , -----

    # ----- . -----

    # ----- / -----

    # ----- PAGEUP -----
    # Reserve: {PAGEUP} -> Previous page (Universal)
    # Reserve: ^{PAGEUP} -> Previous view (Universal)

    ('^!{PAGEUP}', r'D:\Software\A.V.I\Screenshot\PicPick\0\dst\picpick.exe'),

    # ----- PAGEDN -----
    # Reserve: {PAGEDN} -> Next page (Universal)
    # Reserve: ^{PAGEDN} -> Next view (Universal)

    # ----- LMOUSE -----

    # ----- WHEELUP -----

    # Zoom In
    ('^{WheelUp}', SendKeys('<^=')),

    ('!{WheelUp}', SendKeys('{PAGEUP}')),

    # ----- WHEELDN -----

    # Zoom Out
    ('^{WheelDn}', SendKeys('<^-')),

    ('!{WheelDn}', SendKeys('{PAGEDN}')),
]

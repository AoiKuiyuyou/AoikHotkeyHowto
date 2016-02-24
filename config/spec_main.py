# coding: utf-8
#
from __future__ import absolute_import

from contextlib import contextmanager
from functools import partial
from functools import wraps
from os.path import os
from os.path import splitdrive
import time
import webbrowser

import pywinauto
import zbase62.zbase62 as zbase62

from win32clipboard import CloseClipboard
from win32clipboard import EmptyClipboard
from win32clipboard import GetClipboardData
from win32clipboard import OpenClipboard
from win32clipboard import SetClipboardText
from win32con import CF_TEXT
from win32ui import GetForegroundWindow

from aoikhotkey.const import EMASK_V_EFUNC
from aoikhotkey.const import SPEC_SWITCH_V_NEXT
from aoikhotkey.const import SPEC_SWITCH_V_PREV
from aoikhotkey.spec.efunc import efunc_no_mouse
from aoikhotkey.spec.util import Cmd2
from aoikhotkey.spec.util import Send
from aoikhotkey.spec.util import SendSubs
from aoikhotkey.spec.util import SpecReload
from aoikhotkey.spec.util import SpecSwitch

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


###############################################################################


# Send keys
SendKeys = partial(Send, emask=EMASK_V_EFUNC)
# ^ Keep "EMASK_V_EFUNC" on during sending so that we can still see the event,
# even though it does not trigger hotkey (because other emasks are off).


# Send keys and re-press initial modifier keys
SendKeysRepMods = partial(Send, emask=EMASK_V_EFUNC, imod_dn=True)
# ^ Keep "EMASK_V_EFUNC" on during sending so that we can still see the event,
# even though it does not trigger hotkey (because other emasks are off).
#
# ^ "imod_dn" means send "down" event for initial modifier keys in the end.


###############################################################################


# Send substitute string
SendSubsRaw = partial(SendSubs, emask=EMASK_V_EFUNC, raw_yes=True)
# ^ Keep "EMASK_V_EFUNC" on during sending so that we can still see the event,
# even though it does not trigger hotkey (because other emasks are off).
#
# ^ "raw_yes" means interpret the string to send as-is, without special syntax.
# E.g. "{ESC}" means the five characters, not the ESC control character.


###############################################################################


#
def Edit(path):
    """
    An edit command factory method.

    @param path: path of the file to open in an editor.

    @param return: A "Cmd2" object.
    """
    return Cmd2(
        r'D:\Software\Dev\IDE\SublimeText\0\dst\sublime_text.exe',
        path,
    )


###############################################################################


#
def close_foreground_program():
    """
    Close foreground program.
    """
    # Get foreground window handle
    fg_hwnd = GetForegroundWindow().GetSafeHwnd()

    # Get pywinauto window
    window = pywinauto.application.Application().window_(handle=fg_hwnd)

    # If window class is "ConsoleWindowClass"
    if window.Class() == 'ConsoleWindowClass':
        # Use "pywinauto" to close because "ConsoleWindowClass" do not respond
        # to "Alt+F4".
        window.Close()
    # If window class is not "ConsoleWindowClass"
    else:
        # Send "Alt+F4" to close.
        SendKeys('!F4')()


###############################################################################


#
@contextmanager
def clipboard_preserve_context():
    """
    Preserve clipboard value on entering the context, and restore on exiting.
    """
    #
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
        except Exception:
            # Ignore any error
            pass
        finally:
            # Close clipboard
            CloseClipboard()


#
def clipboard_preserve_decorator(func):
    """
    Call the wrapped function in a "clipboard_preserve_context".

    @param func: the wrapped function.

    @param return: the wrapping function.
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


###############################################################################


#
def clipboard_open(try_times=10):
    """
    Open clipboard.

    @param try_times: number of times to try in case of error.
    """
    # Tried times
    tried_times = 0

    while True:
        # Increment tried times
        tried_times += 1

        #
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


#
def clipboard_get_text(to_open=True, to_close=True):
    """
    Get text from clipboard.

    @param to_open: open clipboard before doing.

    @param to_close: close clipboard after done.

    @param return: the text.
    """
    #
    if to_open:
        # Open clipboard
        clipboard_open()

    #
    try:
        # Get text from clipboard
        text = GetClipboardData(CF_TEXT)

        # Return the text
        return text
    finally:
        #
        if to_close:
            # Close clipboard
            CloseClipboard()
    # ^ Raise error


#
def clipboard_set_text(text, to_open=True, to_close=True):
    """
    Set text to clipboard.

    @param text: the text to set.

    @param to_open: open clipboard before doing.

    @param to_close: close clipboard after done.
    """
    #
    if to_open:
        # Open clipboard
        OpenClipboard()

    #
    try:
        # Empty clipboard
        EmptyClipboard()

        # Set text to clipboard
        SetClipboardText(text, CF_TEXT)
    finally:
        #
        if to_close:
            # Close clipboard
            CloseClipboard()
    # ^ Raise error


#
@clipboard_preserve_decorator
def paste_text(text):
    """
    Set text to clipboard and paste.

    @param text: the text to paste.
    """
    # Set text to clipboard
    clipboard_set_text(text)

    # Send "Ctrl+v" to paste
    SendKeysRepMods('^v')()


###############################################################################


#
def base62_text_is_ok(text):
    """
    Check if the text is ok to use.

    @param text: the text to check.
    """
    # Get the first character
    char_first = text[0]

    # If the first character is a digit and is not "0"
    if char_first.isdigit() and char_first != '0':
        return True
    else:
        return False


#
def base62_text_gen(text_length=None, try_times=100):
    """
    Generate a random sequence of bytes, encode it in base62.

    @param try_times: number of times to try.
    @param return: the base62-encoded text.
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


#
@clipboard_preserve_decorator
def id_generate_paste():
    """
    Generate a random base62-encoded text, set it to clipboard and paste.
    """
    # Generate ID text
    id_text = base62_text_gen(text_length=5)

    # Set to clipboard
    clipboard_set_text(id_text)

    # Send "Ctrl+v" to paste
    SendKeysRepMods('^v')()

    # Sleep to keep from being too fast
    time.sleep('0.01')


###############################################################################


#
def transform_special_chars(text):
    """
    Transform text so that it is suitable as file name.

    @param text: the text to transform.

    @param return: the transformed text.
    """
    # Replace "/" with "--".
    # E.g. "pypi.python.org/pypi" becomes "pypi.python.org--pypi".
    text = text.replace('/', '--')

    # Transform special characters
    text_quoted = quote(text, safe="!#$%&'()*+,-.;=@[]^_`{}~ ")

    # Return the transformed text
    return text_quoted


#
def transform_file_path(path):
    """
    Transform a file path until it is not existing, by adding incremented
    number postfix. E.g. "pypi.python.org.url" becomes "pypi.python.org_2.url"

    @param path: the path to transform.

    @param return: the transformed path.
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


#
def create_url_file(url, output_dir):
    """
    Create a ".url" file.

    @param url: the URL value.

    @param output_dir: the output directory path.
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

    #
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

    # Add ".url" file extension
    url_file_name = url_file_name + '.url'

    # Make a file path using the output directory
    url_file_path = os.path.join(output_dir, url_file_name)

    # Transform the file path until it is not existing
    url_file_path = transform_file_path(url_file_path)

    # Create ".url" file content
    url_file_content = '[InternetShortcut]\nURL={}'.format(url)

    # Open output file
    with open(url_file_path, mode='w') as file:
        # Write content to file
        file.write(url_file_content)


#
@clipboard_preserve_decorator
def browser_url_save():
    """
    Read URL from a browser's location bar, save as a ".url" file.
    """
    # Send "Ctrl+l" to move focus to location bar
    SendKeys(r'<^l')()

    # Sleep to keep from being too fast
    time.sleep(0.05)

    # Send "Ctrl+c" to copy the URL in location bar
    SendKeys(r'<^c')()

    # Sleep to keep from being too fast
    time.sleep(0.05)

    # Get the url from clipboard
    text = clipboard_get_text()

    # Move focus off the location bar
    SendKeys('{LAlt}')()

    # Create ".url" file
    create_url_file(url=text, output_dir=r'D:\SoftwareData\URL')


###############################################################################


#
@clipboard_preserve_decorator
def open_parallel_dir(base_dir, create=False):
    """
    Open parallel directory of the current directory in Windows Explorer.
    E.g. jump from "D:\Study\Dev\Lang\Python" to "D:\Software\Dev\Lang\Python".

    @param base_dir: the base directory of the destination directory.

    @param create: create if the destination directory is not existing.
    """
    # Send "Ctrl+l" to move focus to location bar
    SendKeys(r'<^l')()

    # Sleep to keep from being too fast
    time.sleep(0.05)

    # Send "Ctrl+c" to copy the current directory path
    SendKeys(r'<^c')()

    # Get the current directory path from clipboard
    dir_path_in_bar = clipboard_get_text()

    # If current directory is empty
    if not dir_path_in_bar:
        # Exit
        return

    # Remove the "drive" part from the directory path.
    # E.g. "D:\Study" becomes "\Study"
    _, dir_path = splitdrive(dir_path_in_bar)

    # Message
    print(dir_path)

    # Strip slashes
    dir_path = dir_path.strip('\\/')

    # Whether the current directory path starts with any of the prefixes below
    start_with_prefix = False

    # Start to find a matching prefix
    for prefix in [
        'Study',
        'Software',
        'SoftwareData',
        'all\\Software2\\SoftwareBig',
        'all\\Software2\\SoftwareSmall',
    ]:
        # If the current directory path starts with the prefix
        if (dir_path+'\\').startswith(prefix+'\\'):
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


###############################################################################


#
SPEC = [

    ###########################################################################

    # Set event function.
    # A sole "$" is a special value to mean event function.
    ('$', efunc_no_mouse),

    ###########################################################################

    # ESC

    ('+{ESC}', 'B:/'),

    # Reload hotkey spec.
    # A starting "$" means to call in the same thread.
    # "SpecReload" must be called in the same thread.
    ('$#{ESC}', SpecReload),

    #
    ('!{ESC}', partial(open_parallel_dir, base_dir=r'D:/Study')),

    ('#!{ESC}', partial(open_parallel_dir, base_dir=r'D:/Study', create=True)),

    ###########################################################################

    #
    ('::{ESC}1', partial(paste_text, r"""SELECT *
FROM `_TABLE_`
WHERE 1
AND 1
ORDER BY id DESC
LIMIT 10
""")),

    ('::{ESC}2', partial(paste_text, r"""SHOW CREATE TABLE `_TABLE_`""")),

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

    ###########################################################################

    # F1

    ('F1', 'https://www.google.com/'),

    ('!F1', partial(open_parallel_dir, base_dir=r'D:/Software')),

    ('#!F1', partial(open_parallel_dir, base_dir=r'D:/Software', create=True)),

    ('+F1', 'C:/'),

    ###########################################################################

    # F2

    ('F2', 'http://global.bing.com/?setmkt=en-us&setlang=en-us'),

    ('!F2', partial(
        open_parallel_dir, base_dir=r'F:/all/Software2/SoftwareSmall'
    )),

    ('#!F2', partial(
        open_parallel_dir,
        base_dir=r'F:/all/Software2/SoftwareSmall', create=True
    )),

    ('+F2', 'D:/'),

    ###########################################################################

    # F3

    ('F3', 'http://fanyi.baidu.com/'),

    ('!F3', partial(
        open_parallel_dir, base_dir=r'F:/all/Software2/SoftwareBig')),

    ('#!F3', partial(
        open_parallel_dir,
        base_dir=r'F:/all/Software2/SoftwareBig', create=True
    )),

    ('+F3', 'E:/'),

    ###########################################################################

    # F4

    ('F4', 'https://www.baidu.com/'),

    ('+F4', 'F:/'),

    ###########################################################################

    # F5

    ('!F5', partial(open_parallel_dir, base_dir=r'D:/SoftwareData')),

    ('#!F5', partial(
        open_parallel_dir, base_dir=r'D:/SoftwareData', create=True
    )),

    ('+F5', 'G:/'),

    ###########################################################################

    # F6

    ('+F6', 'H:/'),

    ###########################################################################

    # F7

    ###########################################################################

    # F8

    ###########################################################################

    # F9

    ###########################################################################

    # F10

    ###########################################################################

    # F11

    # ('F11', 'Reserved for "Full Screen"'),

    ###########################################################################

    # F12

    ('F12', 'http://127.0.0.1:8000/'),

    ('^F12', 'http://www.taobao.com/'),

    ('!F12', 'https://www.alipay.com/'),

    ###########################################################################

    # `

    ('!`', r'D:\Software\Util\Wox\1.2.0-beta.2\dst\Wox.exe'),

    #
    ('#`', Cmd2(
        r'D:\Software\Util\ProcessUtil\ProcessExplorer\0\dst\procexp.exe'
    )),

    ###########################################################################

    # 1

    ('^1', browser_url_save),

    ('!1', r'D:\Study\Dev\Lang'),

    ('::`12', SendSubsRaw('127.0.0.1')),

    ###########################################################################

    # 2

    ('^2', SendKeysRepMods('^w')),

    ('!2', r'D:\SoftwareData\Dev\Proj'),

    ###########################################################################

    # 3

    ('!3', r'D:\Study\Dev\Lang\Ruby'),

    ###########################################################################

    # 4

    ('^4', r'D:\Software\Net\SSH\WinSCP\0\dst\WinSCP.exe'),

    ('!4', r'D:\Study\Dev\Lang\Java'),

    ###########################################################################

    # 5

    ('!5', r'D:\Study\Dev\Lang\JavaScript'),

    ###########################################################################

    # 6

    ###########################################################################

    # 7

    ('!7', Edit(r'C:\Windows\System32\drivers\etc\hosts')),

    ###########################################################################

    # 8

    ###########################################################################

    # 9

    ###########################################################################

    # 0

    ###########################################################################

    # a

    ('#a', r'E:\all'),

    ('!a', r'D:\Study'),

    ('^!a', r'D:\Study\Dev\Art'),

    ###########################################################################

    # b

    ('$^b', id_generate_paste),

    ('!b', r'D:\Study\Dev\Database'),

    ('#b',
        r'D:\Software\Dev\Database\SQL\MySQL\Client\SQLyog\0\dst\SQLyog.exe'),

    ('^!b', r'D:\Software\Dev\Database'),

    ###########################################################################

    # c

    ('<!c', r'D:\SoftwareCMD'),

    # Use Ctrl+Insert to copy.
    # It works better in console programs like Putty.
    ('^c', SendKeysRepMods(r'^{Insert}')),

    ('#c', r'D:\Study\Dev\Lang\_Comparison'),

    ###########################################################################

    # d

    ('^!d', r'D:\Study\Dev'),

    ('#d', r'C:\Users\Aoik\Downloads'),

    ('!d', r'E:\Download'),

    ###########################################################################

    # e

    ('^e', r'D:\Software\Dev\IDE\SublimeText\0\dst\sublime_text.exe'),

    ('#e', r'D:\Software\Dev\IDE\Notepad++\0\dst\notepad++.exe'),

    ('^+e', r'D:\Software\Dev\IDE\Vim\0\dst\gvim.exe'),

    ('^!e', Edit(
        (
            r'D:\Software\Hotkey\AoikHotkey\.sublimetext'
            r'\AoikHotkey.sublime-project'
        )
    )),

    ###########################################################################

    # f

    # ('^f', 'Reserved for "Find"'),

    ('^!f', Edit(
        r'D:\SoftwareData\FileTypeAsso\AoikWinFileTypeAsso\config.yaml'
    )),

    ###########################################################################

    # g

    # ('^g', 'Reserved for "Goto"'),

    ('!g', r'D:\Study\Dev\VersionControl\Git\Config'),

    ###########################################################################

    # h

    # ('^h', 'Reserved for "Replace"'),

    ('#h', r'C:\Users\Aoik'),

    ###########################################################################

    # i
    ('<^i', Cmd2(
        (
            r'D:\Software\Util\RegistryUtil\AezayRegistryCommander\0\dst'
            r'\RegCmd.exe')
    )),

    ('>^i', 'regedit.exe'),

    ###########################################################################

    # j

    ###########################################################################

    # k

    ('^k', r'D:\Software\A.V.I\Player\PotPlayer\0\dst\PotPlayerMini64.exe'),

    ###########################################################################

    # l

    ('^l', Cmd2(
        'hstart', r'cmd /K polipo_v2.bat'
    )),

    ('!l', r'D:\Software\Language'),

    ###########################################################################

    # m

    ###########################################################################

    # n

    # ('^n', 'Reserved for "New File"'),

    # ('^+n', 'Reserved for "New Window"'),

    ('#n', r'ncpa.cpl'),

    ('!n', r'D:\Study\Net'),

    ###########################################################################

    # o

    ###########################################################################

    # p

    ('<^p', Cmd2('hstart', r'cmd /C python3.bat')),

    ('>^p', Cmd2('hstart', r'cmd /C python2.bat')),

    ('<^!p', r'D:\Software\Dev\Lang\Python\3\dst\Lib\site-packages'),

    ('>^!p', r'D:\Software\Dev\Lang\Python\2\dst\Lib\site-packages'),

    ('#p', r'appwiz.cpl'),

    ('!p', r'D:\Study\Dev\Lang\Python'),

    ###########################################################################

    # q

    ('^q', close_foreground_program),

    ('^!q', r'D:\Software\Net\IM\QQ\0\dst\Bin\QQ.exe'),

    ###########################################################################

    # r

    ###########################################################################

    # s

    ('#s', r'services.msc'),

    ('!s', r'D:\Software'),

    ###########################################################################

    # t

    ('^t', r'D:\Software\Net\SSH\Putty\0\dst\PuTTYPortable.exe'),

    # ('^+t', 'Reserved for "Reopen last tab"'),

    ###########################################################################

    # u

    ###########################################################################

    # v

    # Use "Ctrl+Insert" to paste.
    # It works better in console programs like Putty.
    ('^v', SendKeysRepMods(r'+{Insert}')),

    ###########################################################################

    # w

    ('^!w', r'D:\Software\A.V.I\Player\foobar2000\0\dst\foobar2000.exe'),

    ('#!w', r'D:\Study\Dev\Lang\Python\WebFramework'),

    ('!w', r'D:\SoftwareData\URL'),

    ###########################################################################

    # x

    ###########################################################################

    # y

    ('#y', r'D:\Software\Net\Download\Thunder\0\dst\Program\Thunder.exe'),

    ###########################################################################

    # z

    ('^!z', r'D:\SoftwareCMD\cmd_runasadmin.lnk'),

    ('!z', Cmd2('hstart', r'cmd /K D:\SoftwareCMD\clink_v2.bat')),

    ###########################################################################

    # -

    ###########################################################################

    # =

    ('^=', r'diskmgmt.msc'),

    ###########################################################################

    # [

    ('$^![', SpecSwitch(SPEC_SWITCH_V_PREV)),

    ###########################################################################

    # ]

    ('$^!]', SpecSwitch(SPEC_SWITCH_V_NEXT)),

    ###########################################################################

    # \

    ###########################################################################

    # ;

    ###########################################################################

    # '

    ###########################################################################

    # ,

    ###########################################################################

    # .

    ###########################################################################

    # /

    ###########################################################################

    # PageUp

    ('^{PgUp}', r'D:\Software\A.V.I\Screenshot\PicPick\0\dst\picpick.exe'),

    ###########################################################################

    # PageDn

    # WheelUp

    # Zoom In
    ('^{WheelUp}', SendKeysRepMods('<^=')),

    ('!{WheelUp}', SendKeys('{PgUp}')),

    ###########################################################################

    # WheelDn

    # Zoom Out
    ('^{WheelDn}', SendKeysRepMods('<^-')),

    ('!{WheelDn}', SendKeys('{PgDn}')),

    ###########################################################################

]

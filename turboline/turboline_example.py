#!/usr/bin/env python

""" A simple example of how to use TurboLine"""

import curses
import os
from turboline import TurboLineCmd, TurboLine

class ExampleCommands(TurboLineCmd):
    """
    This is a simple commands example. It defines some commands, a help handler and one argument completer.
    """

    def __init__(self):
        """
        Initialize the super class (must be done).
        """
        TurboLineCmd.__init__(self)

    # A command with auto completable parameters (see complete_welcome command).
    def do_greet(self, argument):
        """
        Greets the user with the given name. Usage: greet name (auto-completable)
        """
        if argument == 'donnie':
            self.write("Why are you wearing that stupid man suit?")
        elif argument == 'frank':
            self.write("Why are you wearing this stupid bunny suit?")
        else:
            self.write("Why aren't you wearing a suit?")

    def complete_greet(self, argument, iteration):
        """
        A simple argument completer. Shows how to use the auto match list method.
        The signature must match this one (argument, iteration).
        :param argument: The argument which should be completed (provided by the user).
        :param iteration: The iteration count (provided by the TurboLineCmd).
        :return: The match for the given iteration or None, if nothing matches.
        """
        allowed_arguments = ['donnie', 'gretchen', 'frank']
        return self._auto_match_list('greet', argument, allowed_arguments, iteration)

    # The signature must always contain the argument parameter, even if we do not need it.
    def do_wake(self, argument):
        """
        A seriously worded instruction to end sleeping. Usage: wake
        """
        self.write("Wake up!")

    # Command using colors
    def do_doomsday(self, argument):
        # No Python doc, we define a little help method below!
        self.write("28 days, 6 hours, 42 minutes, 12 seconds.", curses.color_pair(2))

    # Manually defined help method
    def help_doomsday(self):
        """
        If such a help method is defined, 'help command_name' calls this method
        instead of printing the Python doc.
        """
        self.write("That is when the world will end. Don't ask why.", curses.color_pair(2) | curses.A_BOLD)

    def show_error_message(self, text):
        """
        By overwriting the error message, you can change the style
        or target of the error messages.
        :param text: The error message text to show.
        """
        self.write(text, curses.color_pair(1) | curses.A_BOLD)

    @staticmethod
    def do_quit(line):
        """
        A way to quit the application. Try entering just 'q' followed by enter. As long as it can be
        unambiguously matched, it will autocomplete to quit end exit the example.
        :param line:
        """
        exit(0)


def start(stdscrn):
    # Some Curses defaults, we do not want to echo entered keys and do not show the cursor by default.
    curses.noecho()
    curses.curs_set(0)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_MAGENTA, curses.COLOR_BLACK)

    # That is really everything :)
    # We will create a line at the top of the screen (0,0) with a visible size of the standard screens width and a
    # maximum input length of 500 characters.
    max_y, max_x = stdscrn.getmaxyx()
    screen_width = max_x - 1
    turboline = TurboLine(0, 0, screen_width, 500, ExampleCommands())

    stdscrn.refresh()

    # The TurboLine is shown after the user entered ':' in this example - analogue to vim.
    while True:
        in_key = stdscrn.getkey()
        if in_key == ":":
            turboline.input()
            curses.beep()


if __name__ == '__main__':
    # This is _highly_ recommended. By default, NCurses lets the operating system decide, how long a ESC keypress
    # will be delayed until it is passed on to the application. If no default is set, you will have to wait 1000ms
    # every time you press ESC before something happens. 25ms is the delay used by vim. The delay is usually only
    # relevant if you intend to escape entered characters using the escape key anyway.

    # In order to work, this must be called _before_ NCurses is initialized.
    os.environ.setdefault('ESCDELAY', '25')

    curses.wrapper(start)

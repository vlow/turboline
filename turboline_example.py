__author__ = 'engelfl'

from turboline import TurboLineCmd, TurboLine
import curses
import os


class ExampleCommands(TurboLineCmd):
    """
    This is a simple commands example. It defines three commands and one argument completer.
    """

    def __init__(self):
        """
        Initialize the super class (must be done).
        :return:
        """
        TurboLineCmd.__init__(self)

    def do_greet(self, argument):
        """
        Greets whoever specified. Usage: greet name
        """
        # We can use self.write to give feedback to the user...
        self.write("hello " + argument)

    # The signature must always contain the argument parameter, even if we do not need it.
    def do_greetfrank(self, argument):
        """
        Greets Frank, the man in the stupid bunny suit. Usage: greetfrank
        """

        self.write("hello frank, why are you wearing this stupid bunny suit?")
        # frank: why are you wearing that stupid man suit?

    def do_spiderpig(self, argument):
        # No Python doc, we define a little help method below!
        self.write("Spiderpig, spiderpig!", curses.color_pair(2))

    def help_spiderpig(self):
        """
        If such a help method is defined, 'help command_name' calls this method
        instead of printing the Python doc.
        """
        self.write("Does whatever a spiderpig does!", curses.color_pair(2) | curses.A_BOLD)

    def do_welcome(self, argument):
        """
        Welcomes the user with the given name. Usage: welcome name (auto-completable)
        """
        self.write("hey " + argument + ", welcome!")

    def complete_welcome(self, argument, iteration):
        """
        A simple argument completer. Shows how to use the auto match list method.
        The signature must match this one (argument, iteration).
        :param argument: The argument which should be completed (provided by the user).
        :param iteration: The iteration count (provided by the TurboLineCmd).
        :return: The match for the given iteration or None, if nothing matches.
        """

        # Some common German first names.
        allowed_arguments = ['florian', 'fabian', 'moritz']
        return self._auto_match_list('welcome', argument, allowed_arguments, iteration)

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

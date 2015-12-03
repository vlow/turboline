# turboline
Turboline offers a powerful and easy to use command line for Python 3 programs using curses. It is similar to the Python *cmd* module in API and handling but offers vim-like auto-completion and screen-wrapping. It relies only on core modules and does therefore not create any new dependencies apart from itself. Since it uses the curses module, it is intended for Linux (or Cygwin) use only.

## TL'DR
Want a vim-like input line in your curses program? Take a look at turboline_example.py and get going!

## Description
The Python *cmd* module is a powerful tool to create a fast way of controlling your program in next to no time. Unfortunately, the *cmd* module is not compatible with curses, because it relies on readline and writes directly to stdout. Since curses does not easily allow us to use readline for i/o, turboline replaces the readline functionality of *cmd* to work seamlessly with curses.

Additionally, turboline offers vim-like command and parameter completion/expansion, bash-like history features and screen-wrapping using curses-pads. It also features an adjusted version of the 'help' command, which works with a single line as output.

## Features
From end-user perspective, turboline offers a familiar interface. It resembles the behavior of well known tools like vim, emacs and bash.

### Movement Commands
Moving the cursor in the command line can simply be done by using the left and right arrow key, the home and the end key. But if you prefer, you can always just use the emacs-style movement commands: 

Keystroke | Action
--- | ---
Control-A | Go to left edge of window.
Control-B | Cursor left.
Control-D | Delete character under cursor.
Control-E | Go to end of line.
Control-F | Cursor right.
Control-G | Terminate, returning the line contents.
Control-H | Delete character backward.
Control-K | Clear to end of line.
Control-L | Refresh screen.

These controls are inherited from the curses textpad which is used to render the turboline.

### History
Use the up and down keys to travel through the command history. Page up takes you to the first history entry, page down to the most recent one (bash-like). If you change a command while traveling through the command history, the command is added as a new entry on that exact history position.

[![asciicast](https://asciinema.org/a/30873.png)](https://asciinema.org/a/30873)

### Completion
#### Command-Completion
The command completion matches every possible command which contains the letters of the given input in that order. So if you have a command named 'foobar', you can complete to it from something like 'f' or 'foo' but also 'bar' or even 'fb' by pressing TAB. If there is more than one match, you can cycle through all matches by repeatedly pressing TAB.

[![asciicast](https://asciinema.org/a/30841.png)](https://asciinema.org/a/30841)

#### Argument-Completion
If there are completable parameters defined for a command, you can complete them in the same way.

[![asciicast](https://asciinema.org/a/30842.png)](https://asciinema.org/a/30842)

#### Command-Expansion
If the user input can be unambiguously matched to a command, there is no need to press TAB. The input is auto-expanded to the command when pressing enter. If you have a command named 'quit' and it is the only command containing the letter 'q', the sequence 'q -> Enter' executes quit. Note that there is no auto-expansion for parameters.

[![asciicast](https://asciinema.org/a/30843.png)](https://asciinema.org/a/30843)

### Screen Wrapping
If you're running out of screen, turboline automatically starts to scroll the command line. You can specify the exact size of the turboline and since we never start to wrap lines, your screen layout stays intact no matter what.

[![asciicast](https://asciinema.org/a/30867.png)](https://asciinema.org/a/30867)

### Help
The input 'help command\_name' automatically prints the doc string for the command into the command line. It is also possible to define a custom help command for every command.

[![asciicast](https://asciinema.org/a/30871.png)](https://asciinema.org/a/30871)

## Make it your own
Turboline is very easy to use in your own application. Just import the Python module, define a Command-Class and specify where on the screen you want the turboline to appear. Take a look at the turboline_example.py file for an easy quickstart.

### Command Class
Specify all commands you wish to be available to turboline in a command class. The class has to be derived from TurboLineCmd. For every command, define a function named do_commandname(self, arguments). The arguments parameter is a single string containing everything the user typed after the command name.

If you also want to provide parameter completion for a command, specify complete_commandname(self, line, iteration) and make it return a complete expanded commandline (e.g. 'commandname parameter'). There is a simple helper method called \_auto\_match\_list which does all the heavy-lifting. Take a look at the turboline_example.py, to see how this works.

If you want to specify a custom help behavior, just define a help\_commandname function. This function is automatically called if the user enters 'help commandname' or something which is auto-expandable to that. If no dedicated help method is defined for a command, the function doc-string is returned.

You can also change the behavior for invalid or empty input. Just look at the example file.

A simple command class could look like that:

```python
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
        return self._auto_match_list('welcome', argument, allowed_arguments, iteration)

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
```

### Placing the turboline in your program
To use the turboline in your program, initialize it like that:
```python
    # We use the screen width for the turboline width here, but you can use anything <= screen-width
    max_y, max_x = stdscrn.getmaxyx()
    screen_width = max_x - 1
    turboline = TurboLine(y_start=0, x_start=0, width=screen_width, max_length=500, commands=YourCommandClass())

    stdscrn.refresh()

    # The TurboLine is shown after the user entered ':' in this example - analogue to vim.
    while True:
        in_key = stdscrn.getkey()
        if in_key == ":":
            turboline.input()
```

That takes care of everything. You'll get a turboline with the width of your screen, taking up to 500 characters (softly auto-wrapping when the cursor touches the edge of the screen). Pressing colon will show the turboline with a ":" prompt. You can change the prompt by specifying the "prompt" parameter of the turboline init function.

## Disclaimer and Contribution
I am fairly new to Python and I created this mainly on two weekends, so it is probably not bug free. I welcome pull-requests and reported issues to this repo. If you want to contribute features or bugfixes, please make sure to create your pull-request from a feature-branch.

Also, if you are somewhat experienced in Python, I would appreciate if you point out mistakes or bad practices in my code to me.

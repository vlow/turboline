#!/usr/bin/env python

"""A simple but powerful alternative to the Cmd module for Python programs using Curses."""

import curses
import curses.textpad
import re
import cmd

__license__ = "LGPL-3.0"


class TurboLineVisibilityInfo:
    """
    A small data class, holding the current position information for the TurboLine.
    This information is used when refreshing the curses pad contained in the TurboLine.
    """

    def __init__(self, content_pos_y, content_pos_x, top_y, top_x, bottom_y, bottom_x):
        """
        The constructor. Takes the initial parameters for the pad position.
        :param content_pos_y: The y-position of the content. This is usually 0, since we just show one line.
        :param content_pos_x: The x-position of the content. This determines which part of the pad is shown.
        :param top_y: The y-position of the top left corner position of the pad in the standard screen.
        :param top_x: The x-position of the top left corner position of the pad in the standard screen.
        :param bottom_y: The y-position of the bottom right corner position of the pad in the standard screen.
        :param bottom_x: The x-position of the bottom right corner position of the pad in the standard screen.
        """
        self.content_pos_y = content_pos_y
        self.content_pos_x = content_pos_x
        self.top_y = top_y
        self.top_x = top_x
        self.bottom_y = bottom_y
        self.bottom_x = bottom_x


class TurboLineTextbox(curses.textpad.Textbox):
    """
    An adjusted version of the curses Textbox. The vanilla curses textbox is put inside a curses window.
    As a consequence, the maximum text-input length is limited to the screen size. In order to make the
    text input more flexible, this adjusted Textbox utilizes a pad and shares the position information
    with the TurboLine implementation. On every input, the displayed position of the pad is validated
    and adjusted if the cursor is outside the displayed area.
    """

    def __init__(self, target_pad, visibility_info):
        """
        The constructor.
        :param target_pad: The target pad in which the Textbox should live.
        :param visibility_info: The visibility info from TurboLine implementation.
        """
        super().__init__(target_pad, insert_mode=True)
        self.__visibility_info = visibility_info

    def edit(self, validate=None):
        """
        Edit in the widget window and collect the results.
        This method has been adjusted to update the displayed portion of the
        parent pad according to the cursor position.
        :param validate: The validation method. A method which takes the character
                         code of every input and returns it after validation.
        """
        while 1:
            ch = self.win.getch()
            if validate:
                ch = validate(ch)
            if not ch:
                continue
            if not self.do_command(ch):
                break

            refresh_pad_visibility(self.win, self.__visibility_info)

        return self.gather()


class TurboLine:
    """
    The TurboLine is a vim-like CLI for curses applications. It can take and return a user input,
    supports command history and message feedback to the user. If you provide an implementation
    of the cmd-like TurboLineCmd, it also offers vim-like auto-completion and command-completion on input.
    supports auto completion.
    """

    def __init__(self, y_start, x_start, width, max_length, commands=None, prompt=":"):
        """
        The constructor.
        :param y_start: The vertical start position of the command line.
        :param x_start: The horizontal start position of the command line.
        :param width: The width of the command line.
        :param max_length: The maximum allowed length of input (may be longer than the width of the CLI).
        :param commands: A TurboLineCmd object which contains the commands. If no object is provided
                         autocompletion is disabled.
        :param prompt: The prompt to show on input (colon per default).
        """
        self.prompt = prompt
        self.__prompt_window = curses.newwin(1, width, y_start, x_start)
        self.__prompt_window.refresh()
        self.__visibility_info = TurboLineVisibilityInfo(0, 0, y_start, x_start + len(prompt), y_start,
                                                         x_start + width)
        self.y_start = y_start
        self.x_start = x_start
        self.__text_box_window = curses.newpad(1, max_length)
        self.__text_box = TurboLineTextbox(self.__text_box_window, self.__visibility_info)
        self.validator = TurboLineValidator(self.__text_box_window, self.__text_box)
        self.__commands = commands
        if self.__commands is not None:
            assert isinstance(commands, cmd.Cmd)
            self.__commands.set_turboline(self)
            self.validator.set_commands(commands)

    def input(self, preset_text=''):
        """
        Takes input from the user and returns it. If a preset text is given, it is
        inserted at the beginning of the prompt. If a command object has been
        provided to this TurboLine instance, the command is executed directly after
        the input.
        :param preset_text: The text to insert as preset (optional).
        :return: The user input as string.
        """
        # Make sure we start with a clear line.
        self.clear()

        # Draw the prompt and the preset text.
        self.__prompt_window.addstr(0, 0, self.prompt)
        self.__text_box_window.addstr(preset_text)

        # Adjust the beginning of the input pad to start after the prompt.
        self.__visibility_info.top_x = len(self.prompt)
        refresh_pad_visibility(self.__text_box_window, self.__visibility_info)

        self.__prompt_window.refresh()

        # We make sure that the cursor is visible before we start the input and set it back
        # to whatever it was before we started afterwards.
        old_state = curses.curs_set(1)

        # The input ends with a space, we strip that.
        input_text = self.__text_box.edit(self.validator.validate).rstrip()
        curses.curs_set(old_state)

        self.validator.history.append(input_text)
        self.validator.reset()
        self.clear()

        # Execute the according command, if we have a command object.
        if self.__commands:
            self.__commands.onecmd(input_text)
        return input_text

    def output(self, text, format=curses.A_NORMAL):
        """
        Prints the given text as message in the command line.
        :param text: The text to show.
        :param format: Text format parameters.
        """
        # We should make sure that there is no linebreak in the output text,
        # since we only have one line to show...
        adjusted_text = text.replace('\n', ' ')

        # Also, we remove leading and trailing spaces and tabs.
        # This is important if we're printing out Python doc, as
        # our help implementation does.
        adjusted_text = adjusted_text.strip('\t')
        adjusted_text = adjusted_text.strip()
        self.__text_box_window.addstr(0, 0, adjusted_text, format)

        # We do not want to show a prompt, so we move the pad to the beginning of the line.
        self.__visibility_info.top_x = 0
        self.__prompt_window.refresh()
        refresh_pad_visibility(self.__text_box_window, self.__visibility_info, True)

    def get_history(self):
        """
        Gets the command history from the embedded validator.
        :return: A list of strings containing the recently entered commands.
        """
        return self.validator.history

    def set_history(self, history):
        """
        Sets the history available in the command line.
        :param history: A list of commands which will be available as history.
        """
        self.validator.history = history

    def clear(self):
        """
        Clears the line from all content.
        """
        self.__text_box_window.clear()
        self.__prompt_window.clear()
        self.__prompt_window.refresh()
        pass


class TurboLineValidator:
    """
    The content validator. The validator parses any given key input and adjusts
    it to reflect the desired behavior of the vim-like input line.
    """

    def __init__(self, textbox_target_pad, textbox):
        """
        The constructor.
        :param textbox_target_pad: The pad which contains the Textbox.
        :param textbox: The Textbox object itself.
        """
        self.history = list()
        self.textbox_target_pad = textbox_target_pad
        self.textbox = textbox
        self.history_pos = 0
        self.completion_iteration = 0
        self.completion_text = None
        self.__commands = None

    def set_commands(self, commands):
        """
        Takes the TurboLineCmd commands. This setter is used by the
        TurboLine on initialization.
        """
        self.__commands = commands

    def validate(self, ch):
        """
        This is the validation method which resembles most of the vim-like
        behavior. It is called by the Textbox on every user-keypress. It then
        decides what to do depending on the pressed key and usually hands the pressed
        key back to the Textbox when it has been processed.
        """

        # TAB: Autocomplete Matcher (should be the first hit to reset autocomplete iterations if
        # on any other key than TAB.
        if ch == 9:
            if self.__commands:
                current_input = self.textbox.gather().rstrip()
                if self.completion_iteration == 0:
                    self.completion_text = current_input
                best_match = self.__commands.auto_complete_input(self.completion_text, self.completion_iteration)
                if best_match is not None:
                    self.completion_iteration += 1
                    self.textbox_target_pad.clear()
                    self.textbox_target_pad.addstr(0, 0, best_match)
                return ch
        else:
            self.completion_iteration = 0
            self.completion_text = None

        # HOME: Set the cursor to the beginning of the line.
        if ch == 262:
            return 1  # CTRL + A

        # END: Set the cursor to the end of the line.
        if ch == 360:
            return 5  # CTRL + E

        # PAGE_UP: Jump to first history entry (bash-behavior)
        if ch == 339:
            # Nothing to do, we are already there.
            if self.history_pos == 0:
                return ch
            self.__retain_current_input()

            self.history_pos = 0
            self.textbox_target_pad.addstr(0, 0, self.history[self.history_pos])
            return ch

        # PAGE_DOWN: Jump to last history entry (bash-behavior)
        if ch == 338:
            # Nothing to do, we are already there.
            if self.history_pos > len(self.history) - 2:
                return ch
            self.__retain_current_input()

            self.history_pos = len(self.history) - 1
            self.textbox_target_pad.addstr(0, 0, self.history[self.history_pos])
            return ch

        # UP: Travel up through the history.
        if ch == 259:
            # Prevent out of bounds access
            if self.history_pos == 0:
                return ch
            self.__retain_current_input()

            self.history_pos -= 1
            self.textbox_target_pad.addstr(0, 0, self.history[self.history_pos])
            return ch

        # DOWN: Travel down through the history.
        if ch == 258:
            # Prevent out of bounds access
            if self.history_pos > len(self.history) - 2:
                return ch
            self.__retain_current_input()

            self.history_pos += 1
            self.textbox_target_pad.addstr(0, 0, self.history[self.history_pos])
            return ch

        # DEL: Remove the character under the cursor.
        if ch == 330:
            return 4  # CTRL + D

        # ESC: Cancels the input. Be aware that curses uses the OS default (1000ms) to determine
        # how long it should wait for a subsequent escape sequence key
        # before passing the ESC key on. It is recommended to reduce this
        # delay to 25ms. This is the same delay as vim uses (see:
        # http://stackoverflow.com/questions/27372068/why-does-the-escape-key-have-a-delay-in-python-curses )
        if ch == 27:
            self.textbox_target_pad.clear()
            return 7  # CTRL + G

        return ch

    def __retain_current_input(self):
        """
        Checks the current input. If it differs from the input
        which the history contains for the current history position,
        it creates a new history entry at this position. This resembles
        the very reasonable behavior of the bash-history.
        """
        current_input = self.textbox.gather().rstrip()
        if len(self.history) > self.history_pos:
            if self.history[self.history_pos] != current_input:
                self.history.insert(self.history_pos, current_input)
        else:
            self.history.append(current_input)
        self.textbox_target_pad.clear()

    def reset(self):
        """
        Resets the state of the TurboLine. Must be called by
        the TurboLine after every input.
        """
        self.history = [e for e in self.history if e != '']
        self.history_pos = len(self.history)
        self.completion_iteration = 0


class TurboLineCmd(cmd.Cmd):
    """
    The TurboLineCmd is an adjusted version of the usual Python Cmd. If you are
    not familiar with the concept of the Python Cmd, read: https://docs.python.org/3/library/cmd.html

    The Cmd removes a lot of tedious tasks when handling command input in Python programs. It automatically
    supplies auto-completion, maps input to defined commands and much more.

    You can add your own commands by deriving from TurboLineCmd and define commands named do_commandname. So in
    order to create a command named foo, define a method named do_foo. If you want to provide argument completion
    for this command, provide another method named complete_foo (the above link elaborates this a bit more).

    A lot of functionality comes from readline, which we sadly cannot use in Curses.This adjusted version
    adds a new autocomplete implementation which resembles the vim-input behavior:

    1. Try to complete the command
    2. If there is no argument, TAB cycles through possible matches.
    3. If there is an argument, try to complete the command unambiguously.
    4. If the command is valid, try to complete the argument by calling the corresponding complete_commandname method.

    There is a simple helper called _auto_match_list which can be used in argument completion methods (see the
    documentation on it).
    """

    def __init__(self):
        """
        The constructor.
        """
        cmd.Cmd.__init__(self)
        self.__turboline = None

        # We collect the method names at construction time, so we do not have to
        # do reflection magic every time we want to autocomplete something.
        method_names = dir(self.__class__)
        self.__command_names = [c[3:] for c in method_names if c.startswith('do_')]
        self.__completion_names = [c[9:] for c in method_names if c.startswith('complete_')]
        self.__help_names = [c[5:] for c in method_names if c.startswith('help_')]

    def set_turboline(self, turboline):
        """
        A setter for the TurboLine itself. Only used by the TurboLine.
        """
        self.__turboline = turboline

    def write(self, text, format=curses.A_NORMAL):
        """
        This method is used to write text back to the line (e.g. "Unknown command: ...").
        :param text: The text to write.
        :param format: Curses format parameters.
        """
        self.__turboline.output(text, format)

    def emptyline(self):
        """
        If we do not overwrite the default behavior, an empty input repeats the last
        successful input. This differs from the usual vim/bash behavior, so we just ignore empty
        commands.
        """
        pass

    def do_help(self, arguments):
        """
        Shows the default help string or calls a custom help method if one is defined.
        :param arguments: The arguments which were given to the help command.
        """
        if arguments == '':
            self.write('Usage: help command_name')
            return

        completed_command = self.__complete_command_unambiguously(arguments)
        if completed_command is None:
            self.write('Unknown or ambiguous command: \'' + arguments + '\'. Usage: help command_name')
            return

        if completed_command in self.__help_names:
            help_method = getattr(self, 'help_' + completed_command)
            help_method()
            return

        doc = getattr(self, 'do_' + completed_command).__doc__
        if doc:
            self.write(doc)
        else:
            self.write('No documentation available for \'' + completed_command + '\'')

    def complete_help(self, arguments, iteration):
        """
        Our implementation of complete_... differs from the cmd implementation in that
        it does not return a list, but only one value. We therefore overwrite the
        complete_help to make use of the auto matcher.
        :param arguments: The arguments given to help command (as one string).
        :param iteration: The iteration count. The iteration is done modulo the amount of possible matches.
        :return: The matched command, or None if there is no match.
        """
        return self._auto_match_list('help', arguments, self.__command_names, iteration)

    def default(self, line):
        """
        This method is called if no command matches. Per default, we try to auto-complete the command.
        If we can complete the input unambiguously, we execute the auto-completed command. If this
        fails, we output: "Unknown command: entered_command".

        :param line: The line which was entered by the user.
        """
        command, arguments, parsed_line = self.parseline(line)

        # We allow auto-completable commands
        if command not in self.__command_names:
            possible_command = self.__complete_command_unambiguously(command)
            if possible_command is not None:
                self.onecmd(possible_command + ' ' + arguments)
                return

        self.show_error_message("Unknown command: " + parsed_line)

    def show_error_message(self, text):
        """
        Shows an error message. Overwrite this method to change the
        style or the output of the error message.
        :param text: The text of the error message.
        """
        self.__turboline.output(text, curses.A_BOLD)

    def auto_complete_input(self, text, iteration):
        """
        This method tries to auto-complete the given text. If there is more than one match,
        the given iteration count decides which one will be returned.

        :param text: The text to be completed.
        :param iteration: The iteration count. The iteration is done modulo the amount of possible matches.
        :return: A string with a possible match or None, if nothing matches.
        """
        # Find possible hits
        command, args, line = self.parseline(text)
        possible_command_hits = self.__get_possible_hits(command, self.__command_names)

        # If there are several possible commands, we iterate through them (maintaining the argument).
        if len(possible_command_hits) > 1:
            completion = self.__complete_command(command, iteration)
            if args is not None:
                completion += ' ' + args
            return completion

        # If the command is unambiguously matchable, we try to complete the argument instead.
        elif len(possible_command_hits) == 1:
            new_line = possible_command_hits[0]
            if args is not None:
                new_line += ' ' + args
            return self.__complete_line(new_line, iteration)

        # If nothing matches, we return None.
        else:
            return None

    def __complete_command(self, text, iteration):
        """
        Completes the given text to match a command. If there is more than one match,
        the given iteration count decides which one will be returned.

        :param text: The incomplete command (without arguments).
        :param iteration: The iteration count. The iteration is done modulo the amount of possible matches.
        :return: The matched command or None, if nothing matches.
        """
        hit_list = self.__get_possible_hits(text, self.__command_names)

        if len(hit_list) == 0:
            return None

        return hit_list[iteration % len(hit_list)]

    def __complete_line(self, text, iteration):
        """
        Completes the given line. This method is used to complete input which consists of
        a command(-stub) and argument(s).
        :param text: The input line, which should be completed.
        :param iteration: The iteration count. The iteration is done modulo the amount of possible matches.
        :return: The completed line, or None, if the line cannot be completed.
        """
        command, arguments, line = self.parseline(text)
        if command is None:
            # No command, no completion.
            return None

        # Make sure we have the complete command
        if command not in self.__command_names:
            possible_completion = self.__complete_command_unambiguously(command)
            if possible_completion is None:
                return None
            else:
                command = possible_completion

        # If the user specified a completion, just use that one
        if command in self.__completion_names:
            completion_method = getattr(self, 'complete_' + command)
            return completion_method(arguments, iteration)

        # If not, return whatever we were able to complete
        else:
            return command + ' ' + arguments

    def __get_possible_hits(self, pattern, allowed_words):
        """
        Gets a list of possible matches for the given pattern in the given allowed_words list.

        :param pattern: The search pattern. E.g. "foo"
        :param allowed_words: The list of allowed words (e.g. "foo", "foobar", "bar")
        :return The matches of the given pattern in the given list as a list (e.g. "foo", "foobar")
        """
        regex = self.__create_regex(pattern)

        possible_hits = [c for c in allowed_words if re.match(regex, c)]

        # Empty inputs iterate through everything in allowed_words, but should come back to an empty
        # prompt, once we are all way through the possible matches.
        if pattern is None:
            possible_hits.append('')

        return possible_hits

    def __complete_command_unambiguously(self, text):
        """
        If there is exactly one possible completion for the given incomplete command,
        it is returned, otherwise None.

        :param text: The incomplete command.
        :return The complete command, if there is exactly one match. None otherwise.
        """
        hit_list = self.__get_possible_hits(text, self.__command_names)
        if len(hit_list) != 1:
            return None
        else:
            return hit_list[0]

    def _auto_match_list(self, command, argument, allowed_arguments, iteration):
        """
        This is a simple helper method which can be used to write an argument matcher without much fuzz.
        Provide the command name, the given argument stub, a list of allowed arguments and the iteration
        count and the method returns the whole auto-completed line. If everything in life could be that easy.

        :param command: The command name (e.g. "foo").
        :param argument: The (incomplete) argument (e.g. "bar")
        :param allowed_arguments: A list of allowed arguments (e.g. "bartender", "coffeebar" "persimmon")
        :param iteration: The iteration count. The iteration is done modulo the amount of possible matches.
                          The count is usually given to the argument completion method by the TurboLineCmd.
        :return The complete match for the given iteration count (e.g. "foo bartender" for count 0).
        """
        adjusted_allowed_arguments = list(allowed_arguments)
        adjusted_allowed_arguments.insert(0, '')
        hit_list = self.__get_possible_hits(argument, adjusted_allowed_arguments)
        if len(hit_list) == 0:
            return None
        return command + ' ' + hit_list[iteration % len(hit_list)]

    @staticmethod
    def __create_regex(text):
        """
        Creates a regex pattern, which matches every expression containing the given text in the given order
        but with an arbitrary amount of other characters in between (e.g. foo matches foobar, but also fbarobarobar).
        """
        if text is None:
            return '.*'

        regex = ''
        for letter in text:
            regex += '.*' + letter
        regex += '.*'
        return regex


def refresh_pad_visibility(target_pad, visibility_info, reset_view=False):
    """
    A helper method to refresh the pad and adjusting the displayed portion of
    it to the position of the cursor. If the cursor is outside the displayed
    portion, the left or right end of the displayed portion is moved to the
    cursor position.

    :param target_pad: The pad which contains the TurboLine
    :param visibility_info: The visibility info of the pad.
    :param reset_view: If true, the position is reset to the beginning of the pad.
    """
    current_cursor_pos = target_pad.getyx()

    if reset_view:
        visibility_info.content_pos_x = 0
    else:
        screen_width = visibility_info.bottom_x - visibility_info.top_x
        if current_cursor_pos[1] > visibility_info.content_pos_x + screen_width:
            visibility_info.content_pos_x = current_cursor_pos[1] - screen_width
        elif current_cursor_pos[1] < visibility_info.content_pos_x:
            visibility_info.content_pos_x = current_cursor_pos[1]

    target_pad.refresh(visibility_info.content_pos_y,
                       visibility_info.content_pos_x,
                       visibility_info.top_y,
                       visibility_info.top_x,
                       visibility_info.bottom_y,
                       visibility_info.bottom_x)

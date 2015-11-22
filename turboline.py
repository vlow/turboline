#!/usr/bin/env python
# -*- coding: utf-8 -*-

import curses
import curses.textpad
import os
import re
import cmd


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
                                                         x_start + len(prompt) +
                                                         width)
        self.y_start = y_start
        self.x_start = x_start
        self.__text_box_window = curses.newpad(1, max_length)
        self.__text_box = TurboLineTextbox(self.__text_box_window, self.__visibility_info)
        self.validator = TurboLineValidator(self.__text_box_window, self.__text_box)
        self.__commands = commands
        if self.__commands is not None:
            assert isinstance(commands, cmd.Cmd)
            self.__commands.set_powerline(self)
            self.validator.set_commands(commands)

    def input(self, preset_text=''):
        """
        Takes input from the user and returns it. If a preset text is given, it is
        inserted at the beginning of the prompt. If a command object has been
        provided to this TurboLine instance, the command is executed directly after
        the input.
        :param preset_text: The text to insert as preset (optional).
        :return The user input as string.
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

    def output(self, text):
        """
        Prints the given text as message in the command line.
        :param text The text to show.
        """
        self.__text_box_window.addstr(0, 0, text)

        # We do not want to show a prompt, so we move the pad to the beginning of the line.
        self.__visibility_info.top_x = 0
        self.__prompt_window.refresh()
        refresh_pad_visibility(self.__text_box_window, self.__visibility_info, True)

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
        self.__commands = commands

    def validate(self, ch):

        # TAB: Autocomplete Matcher (should be the first hit to reset autocomplete iterations if
        # on any other key than TAB.
        if ch == 9:
            if self.__commands:
                current_input = self.textbox.gather().rstrip()
                if self.completion_iteration == 0:
                    self.completion_text = current_input
                best_match = self.__commands.complete_input(self.completion_text, self.completion_iteration)
                if best_match:
                    self.completion_iteration += 1
                    self.textbox_target_pad.clear()
                    self.textbox_target_pad.addstr(0, 0, best_match)
        else:
            self.completion_iteration = 0
            self.completion_text = None

        # HOME
        if ch == 262:
            return 1  # CTRL + A

        # END
        if ch == 360:
            return 5  # CTRL + E

        # KEY_UP
        if ch == 259:
            # Prevent out of bounds access
            if self.history_pos == 0:
                return ch
            self.__retain_current_input()

            self.history_pos -= 1
            self.textbox_target_pad.addstr(0, 0, self.history[self.history_pos])

        # KEY_DOWN
        if ch == 258:
            # Prevent out of bounds access
            if self.history_pos > len(self.history) - 2:
                return ch
            self.__retain_current_input()

            self.history_pos += 1
            self.textbox_target_pad.addstr(0, 0, self.history[self.history_pos])

        # DEL
        if ch == 330:
            return 4  # CTRL + D

        # ESC - Be aware that curses uses the OS default (1000ms) to determine
        # how long it should wait for a subsequent escape sequence key
        # before passing the ESC key on. It is recommended to reduce this
        # delay to 25ms. This is the same delay as vim uses (see:
        # http://stackoverflow.com/questions/27372068/why-does-the-escape-key-have-a-delay-in-python-curses )
        if ch == 27:
            self.textbox_target_pad.clear()
            return 7  # CTRL + G

        return ch

    def __retain_current_input(self):
        current_input = self.textbox.gather().rstrip()
        if len(self.history) > self.history_pos:
            if self.history[self.history_pos] != current_input:
                self.history.insert(self.history_pos, current_input)
        else:
            self.history.append(current_input)
        self.textbox_target_pad.clear()

    def reset(self):
        self.history = [e for e in self.history if e != '']
        self.history_pos = len(self.history)
        self.completion_iteration = 0


class TurboLineCmd(cmd.Cmd):
    def __init__(self):
        cmd.Cmd.__init__(self)
        self.__turboline = None
        method_names = dir(self.__class__)
        self.__command_names = [c[3:] for c in method_names if c.startswith('do_')]
        self.__completion_names = [c[9:] for c in method_names if c.startswith('complete_')]

    def set_powerline(self, powerline):
        self.__turboline = powerline

    @staticmethod
    def write(text):
        turboline.output(text)

    def emptyline(self):
        pass

    def default(self, line):
        command, arguments, parsed_line = self.parseline(line)
        # We allow auto-completable commands
        if command not in self.__command_names:
            possible_command = self.__complete_command_unambiguously(command)
            if possible_command is not None:
                self.onecmd(possible_command + ' ' + arguments)
                return
        turboline.output("Unknown command: " + parsed_line)

    def complete_input(self, text, iteration):
        command, args, line = self.parseline(text)
        possible_command_hits = self.__get_possible_hits(command, self.__command_names)
        if len(possible_command_hits) > 1:
            completion = self.__complete_command(command, iteration)
            if args is not None:
                completion += ' ' + args
            return completion
        elif len(possible_command_hits) == 1:
            new_line = possible_command_hits[0]
            if args is not None:
                new_line += ' ' + args
            return self.__complete_line(new_line, iteration)
        else:
            return None

    def __complete_command(self, text, iteration):
        hit_list = self.__get_possible_hits(text, self.__command_names)
        if len(hit_list) == 0:
            return None
        return hit_list[iteration % len(hit_list)]

    def __get_possible_hits(self, text, allowed_words):
        regex = self.__create_regex(text)
        return [c for c in allowed_words if re.match(regex, c)]

    def __complete_command_unambiguously(self, text):
        hit_list = self.__get_possible_hits(text, self.__command_names)
        if len(hit_list) != 1:
            return None
        else:
            return hit_list[0]

    def _auto_match_list(self, command, argument, allowed_arguments, iteration):
        allowed_arguments.insert(0, '')
        hit_list = self.__get_possible_hits(argument, allowed_arguments)
        if len(hit_list) == 0:
            return None
        return command + ' ' + hit_list[iteration % len(hit_list)]

    @staticmethod
    def __create_regex(text):
        regex = ''
        for letter in text:
            regex += '.*' + letter
        regex += '.*'
        return regex

    def __complete_line(self, text, iteration):
        command, arguments, line = self.parseline(text)
        if command is None:
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


class MyCommands(TurboLineCmd):
    def __init__(self):
        TurboLineCmd.__init__(self)

    def do_greet(self, line):
        self.write("hello " + line)

    def do_greetfrank(self, line):
        self.write("hello frank")

    def do_welcome(self, line):
        self.write("welcome " + line)

    def complete_welcome(self, argument, iteration):
        allowed_arguments = ['florian', 'fabian', 'wilhelm']
        return self._auto_match_list('welcome', argument, allowed_arguments, iteration)

    @staticmethod
    def do_quit(line):
        curses.echo()
        screen.clear()
        screen.refresh()
        curses.endwin()
        exit(0)


if __name__ == '__main__':
    os.environ.setdefault('ESCDELAY', '25')
    screen = curses.initscr()
    curses.noecho()
    curses.curs_set(0)
    turboline = TurboLine(0, 0, 40, 500, MyCommands())
    screen.refresh()

    while True:
        in_key = screen.getkey()
        if in_key == ":":
            turboline.input()
        curses.beep()

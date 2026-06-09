import sys
from pathlib import Path
from random import shuffle
from datetime import date, timedelta

from kivy.config import Config
Config.set('kivy', 'exit_on_escape', '0')
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '600')

from kivy.core.text import LabelBase
LabelBase.register(name='Roboto', fn_regular='C:\\Windows\\Fonts\\msyh.ttc')
LabelBase.register(name='RobotoMono', fn_regular='C:\\Windows\\Fonts\\msyh.ttc')
LabelBase.register(name='IPAFont', fn_regular='C:\\Windows\\Fonts\\Arial.ttf')

from kivy.animation import Animation

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.metrics import dp, sp

from data import (get_lesson_words, get_total_lessons,
                  get_all_lesson_numbers, get_score_per_word)
from storage import (init as storage_init, get_user_list, create_user,
                     delete_user, load_user, save_user, get_word_weight, set_word_weight,
                     add_wrong_word, record_wrong_attempt, record_correct_attempt,
                     is_in_wrong_words, get_wrong_words_list,
                     add_to_review_queue, get_today_review, REVIEW_INTERVALS)

# ── Colors ──
C_BG = (0.95, 0.95, 0.98, 1)
C_TEXT = (0.15, 0.15, 0.2, 1)
C_SUBTEXT = (0.4, 0.4, 0.5, 1)
C_PRIMARY = (0.25, 0.60, 0.95, 1)
C_SECONDARY = (1.0, 0.75, 0.10, 1)
C_RED = (0.9, 0.25, 0.2, 1)
C_GREEN = (0.3, 0.8, 0.5, 1)
C_GOLD = (1, 0.85, 0, 1)

def add_bg(widget, color=C_BG):
    with widget.canvas.before:
        Color(*color)
        Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(pos=lambda w, v: setattr(w.canvas.before.children[-1], 'pos', v),
                size=lambda w, v: setattr(w.canvas.before.children[-1], 'size', v))

class CButton(Button):
    def __init__(self, text, on_press=None, bg=C_PRIMARY, size_hint_y=None, height=dp(50), **kw):
        kw.setdefault('font_size', sp(18))
        kw.setdefault('color', (1,1,1,1))
        super().__init__(text=text, **kw)
        self.bg = bg
        self.size_hint_y = size_hint_y
        if height:
            self.height = height
        self.background_color = (0,0,0,0)
        self.bind(pos=self._draw, size=self._draw)
        if on_press:
            self.bind(on_press=on_press)

    def _draw(self, *a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg)
            Rectangle(pos=self.pos, size=self.size)

def top_bar(title, on_back):
    bar = BoxLayout(size_hint_y=None, height=dp(50), padding=[dp(10), dp(5)], spacing=dp(10))
    lbl = Label(text=title, font_size=sp(20), bold=True, color=C_TEXT, size_hint_x=0.7, halign='left', valign='middle')
    bar.add_widget(lbl)
    btn = Button(text='< 返回', size_hint_x=0.25, font_size=sp(15),
                background_color=(0,0,0,0), color=C_PRIMARY)
    btn.bind(on_press=on_back)
    bar.add_widget(btn)
    return bar

# ── Screens ──
class UserSelectScreen(Screen):
    def on_enter(self):
        self.clear_widgets()
        add_bg(self)
        outer = BoxLayout(orientation='vertical', padding=dp(30), spacing=dp(8))
        outer.add_widget(Label(text='选择用户', font_size=sp(28), bold=True, color=C_TEXT,
                                size_hint_y=None, height=dp(60)))
        scroll = ScrollView()
        self.container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6))
        self.container.bind(minimum_height=self.container.setter('height'))
        self.refresh_user_list()
        scroll.add_widget(self.container)
        outer.add_widget(scroll)
        new_btn = CButton('+ 新建用户', bg=C_SECONDARY, on_press=self.new_user)
        outer.add_widget(new_btn)
        self.add_widget(outer)
        self.selected_user = None

    def refresh_user_list(self):
        self.container.clear_widgets()
        for u in get_user_list():
            row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(6))
            name_btn = Button(text=u['name'], font_size=sp(20), size_hint_x=0.7,
                              background_color=(0,0,0,0), color=C_TEXT)
            name_btn.bind(on_press=lambda _, n=u['name']: self.select_user(n))
            row.add_widget(name_btn)
            del_btn = Button(text='X', font_size=sp(16), size_hint_x=0.15,
                            background_color=(0,0,0,0), color=C_RED)
            del_btn.bind(on_press=lambda _, n=u['name']: self.confirm_delete(n))
            row.add_widget(del_btn)
            self.container.add_widget(row)

    def select_user(self, name):
        app = App.get_running_app()
        app.current_user = name
        self.selected_user = name
        for child in self.container.children:
            if not isinstance(child, BoxLayout):
                continue
            for btn in child.children:
                if not isinstance(btn, Button) or btn.size_hint_x < 0.5:
                    continue
                if btn.text == name:
                    btn.background_color = (C_PRIMARY[0], C_PRIMARY[1], C_PRIMARY[2], 0.3)
                    btn.color = (1,1,1,1)
                else:
                    btn.background_color = (0,0,0,0)
                    btn.color = C_TEXT
        Clock.schedule_once(lambda _: setattr(self.manager, 'current', 'main_menu'), 0.15)

    def confirm_delete(self, name):
        box = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        box.add_widget(Label(text=f'确认删除用户「{name}」？\n所有数据将永久丢失', font_size=sp(16), color=C_TEXT))
        btn_row = BoxLayout(spacing=dp(15), size_hint_y=None, height=dp(50))
        pop = Popup(title='删除用户', content=box, size_hint=(0.5, 0.35))
        def do_delete(*a):
            delete_user(name)
            pop.dismiss()
            self.refresh_user_list()
        btn_row.add_widget(CButton('确认删除', bg=C_RED, on_press=do_delete))
        btn_row.add_widget(CButton('取消', bg=(0.7,0.7,0.7,0.5), color=C_TEXT,
                                   on_press=lambda _: pop.dismiss()))
        box.add_widget(btn_row)
        pop.open()

    def new_user(self, *a):
        box = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        inp = TextInput(hint_text='输入昵称', font_size=sp(18), multiline=False, size_hint_y=None, height=dp(50))
        box.add_widget(inp)
        pop = Popup(title='新建用户', content=box, size_hint=(0.6, 0.4))
        def do_create(*a):
            name = inp.text.strip()
            if not name:
                return
            if len(get_user_list()) >= 10:
                p2 = Popup(title='错误', size_hint=(0.5, 0.3))
                p2.content = Label(text='用户已满（最多10人）', color=C_RED)
                p2.open()
                return
            if create_user(name):
                pop.dismiss()
                self.refresh_user_list()
            else:
                p2 = Popup(title='错误', size_hint=(0.5, 0.3))
                p2.content = Label(text='该昵称已存在', color=C_RED)
                p2.open()
        btn = CButton('创建', on_press=do_create)
        box.add_widget(btn)
        pop.open()

class MainMenuScreen(Screen):
    def on_enter(self):
        self.clear_widgets()
        add_bg(self)
        app = App.get_running_app()
        outer = BoxLayout(orientation='vertical', padding=dp(40), spacing=dp(15))
        outer.add_widget(Label(text=f'你好, {app.current_user}!', font_size=sp(28), bold=True,
                                color=C_TEXT, size_hint_y=None, height=dp(60)))
        outer.add_widget(Widget(size_hint_y=None, height=dp(20)))
        outer.add_widget(CButton('[课程] 选择课程', on_press=lambda _: setattr(self.manager, 'current', 'book_select')))
        outer.add_widget(CButton('[打卡] 今日打卡', bg=C_SECONDARY,
                                 on_press=lambda _: setattr(self.manager, 'current', 'review')))
        outer.add_widget(CButton('[错词] 错词库复习', bg=C_RED,
                                 on_press=lambda _: setattr(self.manager, 'current', 'wrong_words')))
        outer.add_widget(CButton('[积分] 积分查看', bg=C_GREEN,
                                 on_press=lambda _: setattr(self.manager, 'current', 'score')))
        outer.add_widget(CButton('< 切换用户', bg=(0.7,0.7,0.7,0.5), color=C_TEXT,
                                 on_press=lambda _: app.switch_user()))
        self.add_widget(outer)
        data = load_user(app.current_user)
        reviews = get_today_review(data)
        if reviews:
            Clock.schedule_once(lambda _: self.show_review_popup(len(reviews)), 0.3)

    def show_review_popup(self, count):
        box = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        box.add_widget(Label(text=f'📅 有 {count} 个词待复习', font_size=sp(20), color=C_TEXT))
        btn_box = BoxLayout(spacing=dp(15), size_hint_y=None, height=dp(50))
        pop = Popup(title='今日打卡', content=box, size_hint=(0.6, 0.4))
        def go(_):
            pop.dismiss()
            self.manager.current = 'review'
        def skip(_):
            pop.dismiss()
        btn_box.add_widget(CButton('去复习', on_press=go))
        btn_box.add_widget(CButton('稍后', bg=(0.7,0.7,0.7,0.5), color=C_TEXT, on_press=skip))
        box.add_widget(btn_box)
        pop.open()

class BookSelectScreen(Screen):
    def on_enter(self):
        self.clear_widgets()
        add_bg(self)
        app = App.get_running_app()
        outer = BoxLayout(orientation='vertical', padding=dp(40), spacing=dp(20))
        outer.add_widget(Widget(size_hint_y=None, height=dp(60)))
        outer.add_widget(Label(text='选择教材', font_size=sp(28), bold=True, color=C_TEXT,
                                size_hint_y=None, height=dp(60)))
        def pick1(_):
            app.selected_book = 1
            self.manager.current = 'lesson_select'
        def pick2(_):
            app.selected_book = 2
            self.manager.current = 'lesson_select'
        outer.add_widget(CButton('新概念英语 第一册', on_press=pick1))
        outer.add_widget(CButton('新概念英语 第二册', bg=C_RED, on_press=pick2))
        outer.add_widget(CButton('< 返回', bg=(0.7,0.7,0.7,0.5), color=C_TEXT,
                                 on_press=lambda _: setattr(self.manager, 'current', 'main_menu')))
        self.add_widget(outer)

class LessonSelectScreen(Screen):
    def on_enter(self):
        self.clear_widgets()
        add_bg(self)
        app = App.get_running_app()
        self.book_id = app.selected_book
        outer = BoxLayout(orientation='vertical')
        outer.add_widget(top_bar('选择课程', lambda _: setattr(self.manager, 'current', 'book_select')))
        scroll = ScrollView()
        self.container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6),
                                    padding=[dp(20), dp(10)])
        self.container.bind(minimum_height=self.container.setter('height'))
        data = load_user(app.current_user)
        lesson_nums = get_all_lesson_numbers(self.book_id)
        unlocked = data['book_progress'][str(self.book_id)]['unlocked_lessons']
        stars = data.get('lesson_stars', {})
        bk = f'book{self.book_id}'
        for ln in lesson_nums:
            lk = f'{bk}_lesson{ln}'
            star_cnt = stars.get(lk, 0)
            if ln > unlocked:
                self.container.add_widget(Label(text=f'[锁] 第{ln}课', font_size=sp(16),
                                                 color=(0.6,0.6,0.6,1), size_hint_y=None, height=dp(40)))
            else:
                s = '*' * star_cnt + '-' * (3 - star_cnt)
                words = get_lesson_words(self.book_id, ln)
                btn = Button(text=f'第{ln}课  {s}  ({len(words)}词)', font_size=sp(16),
                            size_hint_y=None, height=dp(45), background_color=(0,0,0,0), color=C_TEXT)
                btn.bind(on_press=lambda _, x=ln: self.start_lesson(x))
                self.container.add_widget(btn)
        scroll.add_widget(self.container)
        outer.add_widget(scroll)
        self.add_widget(outer)

    def start_lesson(self, lesson_num):
        App.get_running_app().selected_lesson = lesson_num
        self.manager.current = 'game'

class GameScreen(Screen):
    def on_enter(self):
        self.clear_widgets()
        add_bg(self)
        app = App.get_running_app()
        self.book_id = app.selected_book
        self.lesson_num = app.selected_lesson
        self.data = load_user(app.current_user)
        self.words = get_lesson_words(self.book_id, self.lesson_num)
        self.score_per_word = get_score_per_word(self.book_id, self.lesson_num)
        self.setup_ui()
        self.setup_game()

    def setup_ui(self):
        outer = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(8))
        top = BoxLayout(size_hint_y=None, height=dp(35), spacing=dp(8))
        top.add_widget(Button(text='< 退出', font_size=sp(14), size_hint_x=0.2,
                               background_color=(0.7,0.7,0.7,0.5), color=C_TEXT,
                               on_press=lambda _: self.go_back()))
        self.hp_lbl = Label(text='', font_size=sp(20), bold=True, color=C_GOLD,
                             size_hint_x=0.3, halign='center', valign='middle')
        top.add_widget(self.hp_lbl)
        self.score_lbl = Label(text='', font_size=sp(16), color=C_TEXT,
                                size_hint_x=0.3, halign='center', valign='middle')
        top.add_widget(self.score_lbl)
        self.timer_lbl = Label(text='', font_size=sp(18), bold=True, color=C_PRIMARY,
                                size_hint_x=0.2, halign='right', valign='middle')
        top.add_widget(self.timer_lbl)
        outer.add_widget(top)
        outer.add_widget(Widget(size_hint_y=None, height=dp(10)))
        self.chinese_lbl = Label(text='', font_size=sp(36), bold=True, color=C_TEXT,
                                  size_hint_y=None, height=dp(100), opacity=1)
        outer.add_widget(self.chinese_lbl)
        self.phonetic_lbl = Label(text='', font_size=sp(22), color=(0.6,0.4,0.8,1),
                                   size_hint_y=None, height=dp(45), opacity=0, font_name='IPAFont')
        outer.add_widget(self.phonetic_lbl)
        outer.add_widget(Widget(size_hint_y=None, height=dp(8)))
        self.input_txt = TextInput(hint_text='输入英文拼写...', font_size=sp(28), multiline=False,
                                    size_hint_y=None, height=dp(70), padding=[dp(15), dp(10)])
        self.input_txt.bind(on_text_validate=lambda _: self.check_answer())
        outer.add_widget(self.input_txt)
        outer.add_widget(CButton('确认', on_press=lambda _: self.check_answer()))
        self.feedback_lbl = Label(text='', font_size=sp(18), color=C_SUBTEXT, size_hint_y=None, height=dp(50))
        outer.add_widget(self.feedback_lbl)
        self.add_widget(outer)

    def setup_game(self):
        self.word_queue = self.build_weighted_queue()
        self.current_word = None
        self.consecutive_wrong = 0
        self.stars_lost = 0
        self.star_lost_words = set()
        self.total_correct = 0
        self.lesson_complete = False
        self.timer_event = None
        self.time_left = 40
        self.input_txt.disabled = False
        self.update_hp()
        self.update_score()
        self.next_word()

    def update_hp(self):
        remaining = 3 - self.stars_lost
        self.hp_lbl.text = '\u25cf' * remaining + '\u25cb' * (3 - remaining)
        if remaining == 0:
            self.hp_lbl.color = C_RED
        elif remaining <= 1:
            self.hp_lbl.color = C_SECONDARY
        else:
            self.hp_lbl.color = C_GREEN

    def update_score(self):
        total = self.data.get('total_score', 0)
        if total == int(total):
            self.score_lbl.text = f'积分:{int(total)}'
        else:
            self.score_lbl.text = f'积分:{total:.1f}'

    def start_timer(self):
        self.stop_timer()
        self.time_left = 40
        self.timer_lbl.text = f'剩余 {self.time_left}s'
        self.timer_event = Clock.schedule_interval(self.tick, 1)

    def stop_timer(self):
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None

    def tick(self, dt):
        self.time_left -= 1
        self.timer_lbl.text = f'剩余 {self.time_left}s'
        if self.time_left <= 10:
            self.timer_lbl.color = C_RED
        if self.time_left <= 0:
            self.stop_timer()
            self.on_timeout()

    def on_timeout(self):
        self.feedback_lbl.text = '时间到！'
        self.on_wrong()

    def build_weighted_queue(self):
        queue = []
        for w in self.words:
            weight, _, _ = get_word_weight(self.data, self.book_id, self.lesson_num, w.word)
            count = max(1, int(weight * 5))
            for _ in range(count):
                queue.append(w)
        shuffle(queue)
        return queue

    def next_word(self, *a):
        if not self.word_queue:
            self.finish_lesson()
            return
        self.current_word = self.word_queue.pop(0)
        self.consecutive_wrong = 0
        self.chinese_lbl.opacity = 0
        self.chinese_lbl.text = self.current_word.chinese
        anim = Animation(opacity=1, duration=0.25)
        anim.start(self.chinese_lbl)
        self.phonetic_lbl.text = ''
        self.phonetic_lbl.opacity = 0
        self.input_txt.text = ''
        self.feedback_lbl.text = ''
        self.input_txt.focus = True
        self.start_timer()

    def check_answer(self):
        if self.lesson_complete or not self.current_word:
            return
        user_input = self.input_txt.text.strip().lower()
        correct = self.current_word.word.strip().lower()
        if user_input == correct:
            self.on_correct()
        else:
            self.on_wrong()

    def on_correct(self):
        self.consecutive_wrong = 0
        self.total_correct += 1
        score = self.score_per_word
        app = App.get_running_app()
        is_ww = is_in_wrong_words(self.data, self.book_id, self.lesson_num, self.current_word.word)
        if is_ww:
            revived = record_correct_attempt(self.data, self.book_id, self.lesson_num, self.current_word.word)
            self.feedback_lbl.text = '正确！已从错词库复活！' if revived else '正确！还需再对一次才能复活'
        else:
            self.feedback_lbl.text = f'正确！+{score}分'
        self.data['total_score'] = self.data.get('total_score', 0) + score
        weight, _, _ = get_word_weight(self.data, self.book_id, self.lesson_num, self.current_word.word)
        new_weight = max(0.1, weight * 0.8)
        review_dates = [str(date.today() + timedelta(days=i)) for i in REVIEW_INTERVALS]
        set_word_weight(self.data, self.book_id, self.lesson_num, self.current_word.word,
                       new_weight, review_dates)
        save_user(app.current_user, self.data)
        self.input_txt.text = ''
        self.stop_timer()
        self.update_score()
        Clock.schedule_once(self.next_word, 0.8)

    def on_wrong(self):
        self.consecutive_wrong += 1
        word_text = self.current_word.word

        if word_text not in self.star_lost_words:
            self.star_lost_words.add(word_text)
            self.stars_lost += 1
            self.update_hp()

        record_wrong_attempt(self.data, self.book_id, self.lesson_num, word_text)
        self.stop_timer()

        if self.consecutive_wrong == 1:
            self.phonetic_lbl.text = self.current_word.phonetic
            self.phonetic_lbl.opacity = 1
            self.feedback_lbl.text = '再想想！看音标提示'
            self.input_txt.text = ''
            self.input_txt.focus = True
            self.start_timer()
            return

        if self.consecutive_wrong == 2:
            self.feedback_lbl.text = '最后一次机会！'
            self.input_txt.text = ''
            self.input_txt.focus = True
            self.start_timer()
            return

        add_wrong_word(self.data, self.book_id, self.lesson_num,
                      word_text, self.current_word.phonetic, self.current_word.chinese)
        add_to_review_queue(self.data, self.book_id, self.lesson_num,
                           word_text, self.current_word.phonetic, self.current_word.chinese)

        if self.stars_lost >= 3:
            save_user(App.get_running_app().current_user, self.data)
            self.feedback_lbl.text = '失败！错3个词，退出本课'
            Clock.schedule_once(lambda _: self.exit_lesson(), 1.5)
            return

        weight, _, _ = get_word_weight(self.data, self.book_id, self.lesson_num, word_text)
        set_word_weight(self.data, self.book_id, self.lesson_num, word_text, min(2.0, weight * 1.3))
        self.phonetic_lbl.text = ''
        self.phonetic_lbl.opacity = 0
        self.consecutive_wrong = 0
        self.word_queue.append(self.current_word)
        shuffle(self.word_queue)
        self.current_word = self.word_queue.pop(0)
        self.chinese_lbl.text = self.current_word.chinese
        self.chinese_lbl.opacity = 0
        Animation(opacity=1, duration=0.25).start(self.chinese_lbl)
        self.input_txt.text = ''
        self.input_txt.focus = True
        self.start_timer()

    def exit_lesson(self):
        self.stop_timer()
        self.chinese_lbl.text = '再接再厉！'
        self.chinese_lbl.opacity = 1
        self.phonetic_lbl.text = ''
        self.phonetic_lbl.opacity = 0
        self.input_txt.disabled = True
        Clock.schedule_once(lambda _: setattr(self.manager, 'current', 'lesson_select'), 1)

    def finish_lesson(self):
        self.stop_timer()
        self.lesson_complete = True
        self.chinese_lbl.opacity = 1
        if self.stars_lost == 0:
            stars = 3
        elif self.stars_lost <= 2:
            stars = 2
        else:
            stars = 1
        bk = f'book{self.book_id}'
        lk = f'{bk}_lesson{self.lesson_num}'
        if 'lesson_stars' not in self.data:
            self.data['lesson_stars'] = {}
        existing = self.data['lesson_stars'].get(lk, 0)
        if stars > existing:
            self.data['lesson_stars'][lk] = stars
        unlocked = self.data['book_progress'][str(self.book_id)]['unlocked_lessons']
        next_lesson = self.lesson_num + 1
        if next_lesson > unlocked:
            max_lesson = max(get_all_lesson_numbers(self.book_id))
            if next_lesson <= max_lesson:
                self.data['book_progress'][str(self.book_id)]['unlocked_lessons'] = next_lesson
        save_user(App.get_running_app().current_user, self.data)
        self.chinese_lbl.text = '通关！'
        self.phonetic_lbl.text = ''
        self.phonetic_lbl.opacity = 0
        self.input_txt.disabled = True
        self.feedback_lbl.text = f'正确{self.total_correct}次，错误{self.stars_lost}次，获得{"*" * stars}'

    def go_back(self):
        self.stop_timer()
        self.input_txt.disabled = False
        self.manager.current = 'lesson_select'

class WrongWordsScreen(Screen):
    def on_enter(self):
        self.clear_widgets()
        add_bg(self)
        app = App.get_running_app()
        data = load_user(app.current_user)
        outer = BoxLayout(orientation='vertical')
        outer.add_widget(top_bar('错词库', lambda _: setattr(self.manager, 'current', 'main_menu')))
        scroll = ScrollView()
        self.container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(6),
                                    padding=[dp(20), dp(10)])
        self.container.bind(minimum_height=self.container.setter('height'))
        wrong_list = get_wrong_words_list(data)
        if not wrong_list:
            self.container.add_widget(Label(text='错词库为空！', font_size=sp(22), color=C_TEXT,
                                             size_hint_y=None, height=dp(100)))
        for info in wrong_list:
            box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
            box.add_widget(Label(text=f"{info['chinese']} - {info['word']} ({info['phonetic']})",
                                 font_size=sp(14), color=C_TEXT, size_hint_x=0.8))
            btn = Button(text='复习', font_size=sp(14), size_hint_x=0.2,
                        background_color=(0,0,0,0), color=C_PRIMARY)
            btn.bind(on_press=lambda _, i=info: self.review_word(i))
            box.add_widget(btn)
            self.container.add_widget(box)
        scroll.add_widget(self.container)
        outer.add_widget(scroll)
        self.add_widget(outer)

    def review_word(self, info):
        App.get_running_app().wrong_word_review = info
        self.manager.current = 'wrong_word_game'

class WrongWordGameScreen(Screen):
    def on_enter(self):
        self.clear_widgets()
        add_bg(self)
        self.info = App.get_running_app().wrong_word_review
        self.data = load_user(App.get_running_app().current_user)
        self.consecutive_correct = 0
        self.timer_event = None
        self.time_left = 40
        self.setup_ui()

    def setup_ui(self):
        outer = BoxLayout(orientation='vertical', padding=dp(30), spacing=dp(10))
        top = BoxLayout(size_hint_y=None, height=dp(35), spacing=dp(10))
        top.add_widget(Button(text='< 返回', font_size=sp(14), size_hint_x=0.5,
                               background_color=(0.7,0.7,0.7,0.5), color=C_TEXT,
                               on_press=lambda _: setattr(self.manager, 'current', 'wrong_words')))
        self.timer_lbl = Label(text='', font_size=sp(18), bold=True, color=C_PRIMARY,
                                size_hint_x=0.5, halign='right', valign='middle')
        top.add_widget(self.timer_lbl)
        outer.add_widget(top)
        self.chinese_lbl = Label(text=self.info['chinese'], font_size=sp(36), bold=True, color=C_TEXT,
                                  size_hint_y=None, height=dp(100))
        outer.add_widget(self.chinese_lbl)
        self.phonetic_lbl = Label(text='', font_size=sp(24), color=(0.6,0.4,0.8,1),
                                   size_hint_y=None, height=dp(50), opacity=0)
        outer.add_widget(self.phonetic_lbl)
        self.input_txt = TextInput(hint_text='输入英文拼写...', font_size=sp(28), multiline=False,
                                    size_hint_y=None, height=dp(80), padding=[dp(15), dp(15)])
        self.input_txt.bind(on_text_validate=lambda _: self.check_answer())
        outer.add_widget(self.input_txt)
        outer.add_widget(CButton('确认', bg=C_RED, on_press=lambda _: self.check_answer()))
        self.feedback_lbl = Label(text='', font_size=sp(18), color=C_SUBTEXT, size_hint_y=None, height=dp(60))
        outer.add_widget(self.feedback_lbl)
        self.add_widget(outer)
        self.start_timer()

    def start_timer(self):
        self.stop_timer()
        self.time_left = 40
        self.timer_lbl.text = f'剩余 {self.time_left}s'
        self.timer_event = Clock.schedule_interval(self.tick, 1)

    def stop_timer(self):
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None

    def tick(self, dt):
        self.time_left -= 1
        self.timer_lbl.text = f'剩余 {self.time_left}s'
        if self.time_left <= 10:
            self.timer_lbl.color = C_RED
        if self.time_left <= 0:
            self.stop_timer()
            self.on_timeout()

    def on_timeout(self):
        self.feedback_lbl.text = '时间到！'
        self.consecutive_correct = 0
        self.phonetic_lbl.text = self.info.get("phonetic", '')
        self.phonetic_lbl.opacity = 1
        self.input_txt.text = ''
        self.input_txt.focus = True
        self.start_timer()

    def check_answer(self):
        user_input = self.input_txt.text.strip().lower()
        correct = self.info['word'].strip().lower()
        if user_input == correct:
            self.consecutive_correct += 1
            if self.consecutive_correct >= 2:
                self.stop_timer()
                record_correct_attempt(self.data, self.info['book_id'], self.info['lesson'], self.info['word'])
                save_user(App.get_running_app().current_user, self.data)
                self.feedback_lbl.text = '连续对两次！已复活！'
                Clock.schedule_once(lambda _: setattr(self.manager, 'current', 'wrong_words'), 1)
            else:
                self.feedback_lbl.text = f'正确！还需再对一次({self.consecutive_correct}/2）'
                self.input_txt.text = ''
                self.stop_timer()
                Clock.schedule_once(lambda _: self.reset_round(), 1)
        else:
            self.consecutive_correct = 0
            self.phonetic_lbl.text = self.info.get("phonetic", '')
            self.phonetic_lbl.opacity = 1
            self.feedback_lbl.text = '不正确，重新开始计数'
            self.input_txt.text = ''
            self.input_txt.focus = True
            self.start_timer()

    def reset_round(self):
        self.input_txt.text = ''
        self.feedback_lbl.text = ''
        self.phonetic_lbl.text = ''
        self.phonetic_lbl.opacity = 0
        self.input_txt.focus = True
        self.start_timer()

class ReviewScreen(Screen):
    def on_enter(self):
        self.clear_widgets()
        add_bg(self)
        app = App.get_running_app()
        self.data = load_user(app.current_user)
        self.review_queue = get_today_review(self.data)
        self.review_index = 0
        self.current_review = None
        self.setup_ui()
        self.show_next()

    def setup_ui(self):
        outer = BoxLayout(orientation='vertical', padding=dp(30), spacing=dp(10))
        outer.add_widget(Button(text='< 返回', font_size=sp(14), size_hint_y=None, height=dp(35),
                                 background_color=(0.7,0.7,0.7,0.5), color=C_TEXT,
                                 on_press=lambda _: setattr(self.manager, 'current', 'main_menu')))
        outer.add_widget(Label(text='[打卡] 今日打卡复习', font_size=sp(24), bold=True, color=C_TEXT,
                                size_hint_y=None, height=dp(50)))
        self.chinese_lbl = Label(text='', font_size=sp(36), bold=True, color=C_TEXT, size_hint_y=None, height=dp(100))
        outer.add_widget(self.chinese_lbl)
        self.phonetic_lbl = Label(text='', font_size=sp(24), color=(0.6,0.4,0.8,1),
                                   size_hint_y=None, height=dp(50), opacity=0)
        outer.add_widget(self.phonetic_lbl)
        self.input_txt = TextInput(hint_text='输入英文拼写...', font_size=sp(28), multiline=False,
                                    size_hint_y=None, height=dp(80), padding=[dp(15), dp(15)])
        self.input_txt.bind(on_text_validate=lambda _: self.check_answer())
        outer.add_widget(self.input_txt)
        outer.add_widget(CButton('确认', bg=C_SECONDARY, on_press=lambda _: self.check_answer()))
        self.feedback_lbl = Label(text='', font_size=sp(18), color=C_SUBTEXT, size_hint_y=None, height=dp(60))
        outer.add_widget(self.feedback_lbl)
        self.add_widget(outer)

    def show_next(self):
        if self.review_index >= len(self.review_queue):
            self.chinese_lbl.text = '复习完成！'
            self.phonetic_lbl.text = ''
            self.phonetic_lbl.opacity = 0
            self.input_txt.disabled = True
            self.feedback_lbl.text = f'共复习{len(self.review_queue)}个单词'
            return
        self.current_review = self.review_queue[self.review_index]
        self.chinese_lbl.text = self.current_review['chinese'] or '(无中文)'
        self.phonetic_lbl.text = ''
        self.phonetic_lbl.opacity = 0
        self.input_txt.text = ''
        self.input_txt.disabled = False
        self.feedback_lbl.text = ''
        self.input_txt.focus = True

    def check_answer(self):
        if self.current_review is None:
            return
        user_input = self.input_txt.text.strip().lower()
        correct = self.current_review['word'].strip().lower()
        if user_input == correct:
            self.data['total_score'] = self.data.get('total_score', 0) + 0.1
            save_user(App.get_running_app().current_user, self.data)
            self.feedback_lbl.text = '正确！复习+0.1分'
            self.review_index += 1
            Clock.schedule_once(lambda _: self.show_next(), 0.8)
        else:
            self.phonetic_lbl.text = self.current_review.get("phonetic", "")
            self.phonetic_lbl.opacity = 1
            self.feedback_lbl.text = f'不正确，正确答案: {correct}'
            self.review_index += 1
            Clock.schedule_once(lambda _: self.show_next(), 1.5)

class ScoreScreen(Screen):
    def on_enter(self):
        self.clear_widgets()
        add_bg(self)
        app = App.get_running_app()
        data = load_user(app.current_user)
        score = data.get('total_score', 0)
        outer = BoxLayout(orientation='vertical', padding=dp(40), spacing=dp(15))
        outer.add_widget(Label(text='[积分] 我的积分', font_size=sp(24), bold=True, color=C_TEXT,
                                size_hint_y=None, height=dp(50)))
        score_text = f'🏆 {int(score)} 分' if score == int(score) else f'🏆 {score:.1f} 分'
        outer.add_widget(Label(text=score_text, font_size=sp(48), bold=True, color=(1,0.85,0,1),
                                size_hint_y=None, height=dp(120)))
        book1_complete = sum(1 for k, v in data.get('lesson_stars', {}).items()
                            if k.startswith('book1') and v >= 1)
        book2_complete = sum(1 for k, v in data.get('lesson_stars', {}).items()
                            if k.startswith('book2') and v >= 1)
        t1 = get_total_lessons(1)
        t2 = get_total_lessons(2)
        outer.add_widget(Label(text=f'新概念一册：{book1_complete}/{t1} 课通关', font_size=sp(18), color=C_TEXT,
                                size_hint_y=None, height=dp(40)))
        outer.add_widget(Label(text=f'新概念二册：{book2_complete}/{t2} 课通关', font_size=sp(18), color=C_TEXT,
                                size_hint_y=None, height=dp(40)))
        outer.add_widget(Widget(size_hint_y=None, height=dp(60)))
        outer.add_widget(CButton('< 返回', bg=(0.7,0.7,0.7,0.5), color=C_TEXT,
                                 on_press=lambda _: setattr(self.manager, 'current', 'main_menu')))
        self.add_widget(outer)

class WordGameApp(App):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.current_user = None
        self.selected_book = 1
        self.selected_lesson = 1
        self.wrong_word_review = None

    def build(self):
        storage_init()
        sm = ScreenManager()
        sm.add_widget(UserSelectScreen(name='user_select'))
        sm.add_widget(MainMenuScreen(name='main_menu'))
        sm.add_widget(BookSelectScreen(name='book_select'))
        sm.add_widget(LessonSelectScreen(name='lesson_select'))
        sm.add_widget(GameScreen(name='game'))
        sm.add_widget(WrongWordsScreen(name='wrong_words'))
        sm.add_widget(WrongWordGameScreen(name='wrong_word_game'))
        sm.add_widget(ReviewScreen(name='review'))
        sm.add_widget(ScoreScreen(name='score'))
        sm.current = 'user_select'
        return sm

    def switch_user(self):
        self.current_user = None
        self.root.current = 'user_select'

if __name__ == '__main__':
    WordGameApp().run()

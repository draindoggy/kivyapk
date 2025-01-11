from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.dialog import MDDialog
from kivymd.uix.screen import MDScreen
from kivy.uix.scrollview import ScrollView
from kivymd.uix.progressbar import MDProgressBar
from web3 import Web3
import json
import asyncio
from kivy.clock import Clock

infura_url = "https://sepolia.infura.io/v3/a2a128abd3f841b88748ebcd27e9fdb3"
web3 = Web3(Web3.HTTPProvider(infura_url))

contract_address = Web3.to_checksum_address("0xe71d49813e746cd7c844c483b6791cd310e68bc2")
with open("newest_poll.abi", "r") as abi_file:
    contract_abi = json.load(abi_file)

contract = web3.eth.contract(address=contract_address, abi=contract_abi)

class NewPollApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Purple"
        self.main_screen = MDScreen()
        self.main_screen.add_widget(self.main_menu())
        return self.main_screen

    def main_menu(self):
        self.layout = MDBoxLayout(orientation='vertical', padding=10, spacing=10)
        self.layout.add_widget(MDLabel(text='Меню', halign='center', theme_text_color="Primary"))

        self.layout.add_widget(MDRaisedButton(text='Создать новый опрос', on_release=self.create_poll))
        self.layout.add_widget(MDRaisedButton(text='Показать существующие опросы', on_release=self.show_polls))
        self.layout.add_widget(MDRaisedButton(text='Показать результаты', on_release=self.show_results))
        return self.layout

    def create_poll(self, instance):
        self.layout.clear_widgets()
        self.poll_name_input = MDTextField(hint_text='Введите название опроса', mode="rectangle")
        self.layout.add_widget(self.poll_name_input)

        self.options = []
        self.option_layout = MDBoxLayout(orientation='vertical', spacing=5)
        self.layout.add_widget(self.option_layout)

        add_option_button = MDFlatButton(text='Добавить вариант ответа')
        add_option_button.bind(on_release=self.add_option)
        self.layout.add_widget(add_option_button)

        save_poll_button = MDRaisedButton(text='Сохранить опрос')
        save_poll_button.bind(on_release=self.save_poll)
        self.layout.add_widget(save_poll_button)

        back_button = MDFlatButton(text='Назад в меню')
        back_button.bind(on_release=self.back_to_main_menu)
        self.layout.add_widget(back_button)

    def add_option(self, instance):
        option_input = MDTextField(hint_text='Вариант ответа', mode="rectangle")
        self.option_layout.add_widget(option_input)
        self.options.append(option_input)

    def save_poll(self, instance):
        poll_name = self.poll_name_input.text.strip()
        options = [option.text.strip() for option in self.options if option.text.strip()]
        if not poll_name or not options:
            self.show_dialog("Ошибка", "Название опроса или варианты ответа не могут быть пустыми.")
            return

        account = "0x1fFA0ab35Ff6bBcB7f053683F33eb346860aD469"
        private_key = "df0e7350e0560f9ef19039abdf5636c4338ad85662bf2ef9a7259f8634a42217"
        nonce = web3.eth.get_transaction_count(account)

        try:
            transaction = contract.functions.createPoll(poll_name, options).build_transaction({
                'chainId': 11155111,
                'gas': 2000000,
                'gasPrice': web3.to_wei('25', 'gwei'),
                'nonce': nonce,
            })

            signed_txn = web3.eth.account.sign_transaction(transaction, private_key=private_key)
            tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)

            print("Ожидание подтверждения транзакции...")
            tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

            if tx_receipt.status == 1:
                self.show_dialog("Успех", f"Опрос создан. Хэш транзакции: {web3.to_hex(tx_hash)}")
            else:
                self.show_dialog("Ошибка", "Транзакция не была подтверждена.")
        except Exception as e:
            self.show_dialog("Ошибка", f"Ошибка при создании опроса: {str(e)}")

        self.back_to_main_menu()

    def show_polls(self, instance):
        self.layout.clear_widgets()

        # Добавляем надпись "Загрузка"
        self.loading_label = MDLabel(text="загрузка всех опросов...", halign='center', size_hint_y=None, height="30dp")
        self.layout.add_widget(self.loading_label)

        # Добавляем прогресс-бар с уменьшенной высотой
        self.progress_bar = MDProgressBar(height="10dp", size_hint_y=None)
        self.layout.add_widget(self.progress_bar)

        # Запускаем загрузку опросов
        Clock.schedule_interval(self.update_progress, 0.1)  # Обновляем прогресс каждые 0.1 секунды
        Clock.schedule_once(lambda dt: self.load_polls(), 2)  # Задержка для симуляции загрузки

    def update_progress(self, dt):
        # Обновляем прогресс-бар
        if self.progress_bar.value < 100:
            self.progress_bar.value += 5  # Увеличиваем прогресс на 5%
        else:
            Clock.unschedule(self.update_progress)  # Останавливаем обновление

    def load_polls(self):
        try:
            poll_count = contract.functions.getPollCount().call()
        except Exception as e:
            self.show_dialog("Ошибка", f"Не удалось загрузить опросы: {str(e)}")
            return

        # Убираем прогресс-бар и надпись
        self.layout.clear_widgets()

        if poll_count == 0:
            self.layout.add_widget(MDLabel(text="Нет доступных опросов.", halign='center'))
        else:
            scroll_view = ScrollView()
            poll_list_layout = MDBoxLayout(orientation='vertical', padding=10, spacing=10, size_hint_y=None)
            poll_list_layout.bind(minimum_height=poll_list_layout.setter('height'))

            for i in range(poll_count):
                poll = contract.functions.polls(i).call()
                poll_title = poll[0]
                poll_button = MDRaisedButton(text=poll_title)
                poll_button.bind(on_release=lambda instance, index=i: self.open_poll(index))
                poll_list_layout.add_widget(poll_button)

            scroll_view.add_widget(poll_list_layout)
            self.layout.add_widget(scroll_view)

        back_button = MDFlatButton(text='назад в меню')
        back_button.bind(on_release=self.back_to_main_menu)
        self.layout.add_widget(back_button)

    def open_poll(self, poll_index):
        self.layout.clear_widgets()

        # Добавляем надпись "Загрузка"
        self.loading_label = MDLabel(text="загрузка выбранного опроса...", halign='center', size_hint_y=None, height="30dp")
        self.layout.add_widget(self.loading_label)

        # Добавляем прогресс-бар с уменьшенной высотой
        self.progress_bar = MDProgressBar(height="10dp", size_hint_y=None)
        self.layout.add_widget(self.progress_bar)

        # Запускаем загрузку данных опроса
        Clock.schedule_interval(self.update_progress, 0.1)  # Обновляем прогресс каждые 0.1 секунды
        Clock.schedule_once(lambda dt: self.load_poll(poll_index), 2)  # Задержка для симуляции загрузки

    def load_poll(self, poll_index):
        try:
            poll = contract.functions.polls(poll_index).call()
            results_data = contract.functions.getResults(poll_index).call()
        except Exception as e:
            self.show_dialog("ошибка", f"не удалось загрузить данные опроса: {str(e)}")
            return

        if len(results_data) < 2:
            self.show_dialog("ошибка", "Некорректные данные опроса.")
            return

        title = poll
        options = results_data[0]

        # Убираем прогресс-бар и надпись
        self.layout.clear_widgets()
        self.layout.add_widget(MDLabel(text=f"опрос: {title}", halign='center'))

        self.checkboxes = []

        for i, option in enumerate(options):
            option_layout = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=40, spacing=40)

            checkbox = MDCheckbox(group=f"poll_{poll_index}", size_hint=(None, None), size=(30, 30))
            option_layout.add_widget(checkbox)

            option_label = MDLabel(text=f"{option}", halign='left', size_hint_x=None)
            option_layout.add_widget(option_label)

            self.layout.add_widget(option_layout)

            self.checkboxes.append((checkbox, i))

        vote_button = MDRaisedButton(text="проголосовать", on_release=lambda _: self.cast_vote(poll_index))
        self.layout.add_widget(vote_button)

        back_button = MDFlatButton(text='назад в меню')
        back_button.bind(on_release=self.back_to_main_menu)
        self.layout.add_widget(back_button)

    def cast_vote(self, poll_index):
        selected_option = next(((checkbox, index) for checkbox, index in self.checkboxes if checkbox.active), None)
        if selected_option is None:
            self.show_dialog("Ошибка", "Выберите вариант перед голосованием.")
            return

        _, option_index = selected_option

        account = "0x1fFA0ab35Ff6bBcB7f053683F33eb346860aD469"
        private_key = "df0e7350e0560f9ef19039abdf5636c4338ad85662bf2ef9a7259f8634a42217"
        nonce = web3.eth.get_transaction_count(account)

        try:
            transaction = contract.functions.vote(poll_index, option_index).build_transaction({
                'chainId': 11155111,
                'gas': 200000,
                'gasPrice': web3.to_wei('20', 'gwei'),
                'nonce': nonce,
            })

            signed_txn = web3.eth.account.sign_transaction(transaction, private_key=private_key)
            tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)

            self.show_dialog("Успех", f"Голос отправлен. Хэш транзакции: {web3.to_hex(tx_hash)}")
        except Exception as e:
            self.show_dialog("Ошибка", f"Ошибка при голосовании: {str(e)}")

    def show_results(self, instance):
        self.layout.clear_widgets()
        try:
            titles, all_options = contract.functions.getAllPolls().call()
        except Exception as e:
            self.show_dialog("Ошибка", f"Не удалось загрузить результаты: {str(e)}")
            return

        for i, title in enumerate(titles):
            self.layout.add_widget(MDLabel(text=f"Опрос: {title}", halign='center'))
            results = contract.functions.getResults(i).call()

            if isinstance(results, (list, tuple)) and len(results) == 2:
                options, vote_counts = results
                if isinstance(options, (list, tuple)) and isinstance(vote_counts, (list, tuple)) and len(
                        options) == len(vote_counts):
                    for j, option in enumerate(options):
                        self.layout.add_widget(MDLabel(text=f"{option}: {vote_counts[j]} голосов", halign='center'))
                else:
                    self.layout.add_widget(MDLabel(text="Некорректные данные о результатах.", halign='center'))
            else:
                self.layout.add_widget(MDLabel(text="Некорректные данные опроса.", halign='center'))

        back_button = MDFlatButton(text='Назад в меню')
        back_button.bind(on_release=self.back_to_main_menu)
        self.layout.add_widget(back_button)

    def back_to_main_menu(self, instance=None):
        self.layout.clear_widgets()
        self.layout.add_widget(self.main_menu())

    def show_dialog(self, title, message):
        dialog = MDDialog(title=title, text=message, buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())])
        dialog.open()

if __name__ == '__main__':
    NewPollApp().run()
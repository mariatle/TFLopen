import time

import requests
import json

learner_mode = 0
alphabet = "ab"



class Prefix:
    def __init__(self, value, is_main=True):
        self.value = value
        self.is_main = is_main


class Table:
    def __init__(self, prefixes, suffixes):
        self.prefixes = prefixes
        self.suffixes = suffixes
        self.table = {prefix.value: {suffix: '0' for suffix in suffixes} for prefix in prefixes}

    def add_prefix(self, new_prefix):
        if new_prefix.value not in [prefix.value for prefix in self.prefixes]:
            self.prefixes.append(new_prefix)
            self.table[new_prefix.value] = {suffix: '0' for suffix in self.suffixes}
            return True
        return False

    def add_suffix(self, new_suffix):
        if new_suffix not in self.suffixes:
            self.suffixes.append(new_suffix)
            for prefix in self.prefixes:
                self.table[prefix.value][new_suffix] = '0'
            return True
        return False

    def complete_table(self):
        for prefix in self.prefixes:
            if not prefix.is_main:
                # Изначально считаем, что эквивалентный главный префикс не найден
                has_equivalent_main = False

                # Проверяем, есть ли эквивалентная строка у главных префиксов
                for main_prefix in [p for p in self.prefixes if p.is_main]:
                    if all(self.table[prefix.value][suffix] == self.table[main_prefix.value][suffix] for suffix in
                           self.suffixes):
                        has_equivalent_main = True
                        break

                # Если эквивалентного главного префикса не найдено, то текущий префикс становится главным
                if not has_equivalent_main:
                    prefix.is_main = True

    def inconsistency_table(self):
        for i in range(len(self.prefixes)):
            prefix1 = self.prefixes[i]
            if not prefix1.is_main:
                continue
            for j in range(i + 1, len(self.prefixes)):
                prefix2 = self.prefixes[j]
                if not prefix2.is_main:
                    continue
                if all(self.table[prefix1.value][suffix] == self.table[prefix2.value][suffix] for suffix in
                       self.suffixes):
                    for suffix in self.suffixes:
                        for letter in alphabet:
                            word1 = prefix1.value + letter + suffix
                            word2 = prefix2.value + letter + suffix
                            flag1 = ask_for_word(word1)
                            flag2 = ask_for_word(word2)
                            if flag1 != flag2:
                                new_suffix = letter + suffix
                                self.add_suffix(new_suffix)
                                return True
        return False

    def print_table(self):
        for prefix in self.prefixes:
            for suffix in self.suffixes:
                print(f"{prefix.value} + {suffix}: {self.table[prefix.value][suffix]}")


def ask_for_word(word):
    if learner_mode == 0:
        answer = input(f"Принадлежит ли '{word}' языку? (1/0): ")
        if answer == "1":
            return True
        else:
            return False
    else:
        # Серверный режим
        url = "http://localhost:8080/checkWord"
        try:
            payload1 = {'word': word}
            response = requests.post(url, json=payload1)
            data = response.json()
            result = data.get("response", "")
            if result == "1":
                return True
            elif result == "0":
                return False
        except requests.RequestException as e:
            print(f"Ошибка запроса: {e}")
            return False


def ask_for_table(table):
    if learner_mode == 0:
        table.print_table()
        correct = input("Таблица верна? (true/false): ")
        if correct.lower() == "true":
            return "true", ""
        else:
            counterexample = input("Введите контрпример: ")
            counterexample_type = input("true если пример не принадлежит лернеру, иначе false: ")
            return counterexample, counterexample_type
    else:
        # Серверный режим
        main_prefixes = [p.value for p in table.prefixes if p.is_main]
        non_main_prefixes = [p.value for p in table.prefixes if not p.is_main]
        suffixes = table.suffixes
        table_data = []

        # Собираем данные из таблицы
        for prefix in main_prefixes + non_main_prefixes:
            for suffix in suffixes:
                table_data.append('1' if table.table[prefix][suffix] == '+' else '0')

        url = "http://localhost:8080/checkTable"
        try:
            payload2 = {
                "main_prefixes": " ".join(main_prefixes),
                "non_main_prefixes": " ".join(non_main_prefixes),
                "suffixes": " ".join(suffixes),
                "table": " ".join(table_data)
            }
            response = requests.post(url, json=payload2)
            data = response.json()
            if data["response"] == "true":
                return "true", ""
            else:
                return data["response"], "true" if data["type"] else "false"
        except requests.RequestException as e:
            print(f"Ошибка запроса: {e}")
            return "ERROR", "ERROR"


def set_mode_for_mat(mode):
    url = "http://localhost:8080/generate"
    try:
        response = requests.post(url, json={"mode": mode})
        response.raise_for_status()
        data = response.json()
        return data["maxLexemeSize"], data["maxBracketNesting"]
    except requests.RequestException as e:
        print(f"Ошибка запроса: {e}")
        return None, None


def main():
    epsilon = 'ε'


    is_done = False

    prefixes = [Prefix(epsilon)]
    suffixes = [epsilon]
    et = Table(prefixes, suffixes)

    while not is_done:
        for prefix in et.prefixes:
            for suffix in et.suffixes:
                if et.table[prefix.value][suffix] == '0':
                    word = prefix.value + suffix if prefix.value != "ε" else suffix
                    value = '+' if ask_for_word(word) else '-'
                    et.table[prefix.value][suffix] = value

        for old_prefix in et.prefixes:
            if old_prefix.is_main:
                current_prefix = old_prefix.value
                if current_prefix == "ε":
                    current_prefix = ""
                for letter in alphabet:
                    new_prefix = Prefix(value=current_prefix + letter, is_main=False)
                    if et.add_prefix(new_prefix):
                        for suffix in et.suffixes:
                            current_suffix = suffix
                            if current_suffix == "ε":
                                current_suffix = ""
                            word = new_prefix.value + current_suffix
                            value = '+' if ask_for_word(word) else '-'
                            et.table[new_prefix.value][suffix] = value

        et.complete_table()

        if not all(prefix.is_main for prefix in et.prefixes):
            while et.inconsistency_table():
                for prefix in et.prefixes:
                    for suffix in et.suffixes:
                        if et.table[prefix.value][suffix] == '0':
                            current_suffix = suffix
                            if current_suffix == "ε":
                                current_suffix = ""
                            word = prefix.value + current_suffix
                            value = '+' if ask_for_word(word) else '-'
                            et.table[prefix.value][suffix] = value

            counterexample, type_example = ask_for_table(et)

            if type_example == "":
                is_done = True
            else:
                for i in range(len(counterexample)):
                    et.add_suffix(counterexample[i:])

    et.print_table()


if __name__ == "__main__":
    main()

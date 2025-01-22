from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_apps_murkup():
    """ Inline buttons для выдачи ссылок на скачивание приложений """
    actions = InlineKeyboardMarkup(row_width=3)

    actions.add(InlineKeyboardButton(text="Windows", url="https://github.com/hiddify/hiddify-next/releases/"
                                                         "download/v2.0.5/Hiddify-Windows-Setup-x64.exe"),
                InlineKeyboardButton(text="MacOS", url="https://github.com/hiddify/hiddify-next/"
                                                       "releases/download/v2.0.5/Hiddify-MacOS.dmg"),
                InlineKeyboardButton(text="Linux", url="https://github.com/hiddify/hiddify-next/releases/"
                                                       "download/v2.0.5/Hiddify-Debian-x64.deb")
                )
    actions.add(InlineKeyboardButton(text="iOS", url="https://github.com/hiddify/hiddify-next/"
                                                     "releases/download/v2.0.5/Hiddify-iOS.ipa"),
                InlineKeyboardButton(text="Android", url="https://github.com/hiddify/hiddify-next/releases/"
                                                         "download/v2.0.5/Hiddify-Android-universal.apk")
                )
    actions.add(InlineKeyboardButton(text="Выбрать свой вариант", url="https://github.com/hiddify/"
                                                                      "hiddify-app/releases/tag/v2.0.5"))
    return actions

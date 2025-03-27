from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from i18n_middleware import _


def get_apps_murkup():
    """ Inline buttons для выдачи ссылок на скачивание приложений """
    actions = InlineKeyboardMarkup(row_width=3)

    actions.add(InlineKeyboardButton(text="💻 Windows", url="https://github.com/hiddify/hiddify-next/releases/"
                                                         "download/v2.0.5/Hiddify-Windows-Setup-x64.exe"),
                InlineKeyboardButton(text="🍏 MacOS", url="https://apps.apple.com/ru/app/"
                                                       "hiddify-proxy-vpn/id6596777532"),
                InlineKeyboardButton(text="🐧 Linux", url="https://github.com/hiddify/hiddify-next/releases/"
                                                       "download/v2.0.5/Hiddify-Debian-x64.deb")
                )
    actions.add(InlineKeyboardButton(text="📱 iOS", url="https://apps.apple.com/ru/app/v2raytun/id6476628951"),
                InlineKeyboardButton(text="🤖 Android", url="https://play.google.com/store/"
                                                         "apps/details?id=app.hiddify.com")
                )
    actions.add(InlineKeyboardButton(text=_("🔀 Другой вариант"), url="https://github.com/hiddify/"
                                                                      "hiddify-app/releases/tag/v2.0.5"))
    return actions

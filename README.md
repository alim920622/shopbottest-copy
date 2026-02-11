# agregate-bot



## Проверки i18n (клиентский контур)

```bash
rg -n "[А-Яа-яЁё]" app/handlers_client app/services app/ui
rg -n "InlineKeyboardButton\(text=" app/handlers_client app/services app/ui
rg -n "\bt\(" app/handlers_client app/services app/ui
```

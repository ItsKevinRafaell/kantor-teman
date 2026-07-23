# Target: /root/.hermes/shared/scripts/calendar_client.py
# Fix CALENDAR_ALIASES to exact calendar ids from `list` output.
# Gmail dots-optional makes temanumkmkita@gmail.com often work, but list id is temanumkm.kita@gmail.com.

# BEFORE:
# CALENDAR_ALIASES = {
#     "pribadi": "kevin.sabran@gmail.com",
#     "temanumkmkita": "temanumkmkita@gmail.com",
# }

# AFTER:
CALENDAR_ALIASES = {
    "pribadi": "kevin.sabran@gmail.com",  # Mika
    "temanumkmkita": "temanumkm.kita@gmail.com",  # Nara (exact id from calendar list)
    "teman": "temanumkm.kita@gmail.com",
}

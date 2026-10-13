"""Shared display convention; never infer surname boundaries from legacy text."""
def person_name(user):
    return ' '.join(part.strip() for part in (user.last_name,user.first_name) if part.strip()) or user.username

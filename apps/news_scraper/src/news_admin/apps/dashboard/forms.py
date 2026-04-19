from __future__ import annotations

from collections.abc import Iterable

from django import forms


class SeedJobForm(forms.Form):
    domain = forms.ChoiceField(label="Domain")

    def __init__(
        self,
        *args,
        domains: Iterable[str] = (),
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.fields["domain"].choices = [(domain, domain) for domain in domains]

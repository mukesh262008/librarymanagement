# Central Library

A local library operations platform built with Flask, SQLite, HTML, CSS and JavaScript.

## Run locally

1. Create and activate a Python virtual environment.
2. Install dependencies with `python -m pip install -r requirements.txt`.
3. Start the application with `python app.py`.
4. Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

The SQLite database is created at `instance/library.db` on first start and populated with stable sample members, 100 additional catalogue titles, loans, fines and policies. Existing database records are preserved on subsequent starts.

On first start, the application opens a one-time staff account setup page. Choose a username and a password of at least 12 characters; the password is stored as a one-way hash. Future visits require staff sign-in. The session signing key is generated locally in `instance/session.key`; set `LIBRARY_SECRET_KEY` in the environment to provide a deployment-managed key.

## Application areas

- **Overview** — operational metrics, recent circulation activity and items requiring attention.
- **Members** — member search, account filters, loan history and fine balances.
- **Catalogue** — title, author and ISBN search, category and availability filters, and item history.
- **Circulation** — eligibility checks, issue, return, renewal, policy explanations and a form to add Student or Staff members.
- **Rules & Policies** — active borrowing, renewal and fine policies.

Circulation decisions are evaluated on the server against the active policies stored in SQLite.

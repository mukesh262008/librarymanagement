
# Intelligent Library Rule Management System

A modern library management platform that automates borrowing, renewal, return, fine, restriction, and eligibility decisions using a centralized rule-based decision engine.

The system combines library operations with logical reasoning to provide **consistent, transparent, and explainable decisions** for members and library staff.

---

## Overview

Managing library operations often requires checking multiple conditions before approving an action.

For example, before issuing a book, the system may need to verify:

* Member account status
* Current number of borrowed books
* Overdue items
* Outstanding fines
* Book availability
* Renewal eligibility
* Applicable library policies

The **Intelligent Library Rule Management System** evaluates these conditions automatically and provides a clear decision along with the reason behind it.

### Example

**Request:** Borrow a book

**Account Conditions:**

* No active restrictions
* 2 books currently borrowed
* No overdue books
* No unpaid fines
* Requested book available

**Decision:**
`Borrowing Approved`

If the member has an overdue book:

**Decision:**
`Borrowing Not Approved`

**Reason:**
`Member has an overdue item.`

---

## Key Features

### Member Management

* Member profiles
* Account status
* Current loans
* Borrowing history
* Fine information
* Restrictions

### Catalogue Management

* Book title and author
* ISBN
* Categories
* Availability status
* Search and filtering

### Circulation Management

* Issue books
* Return books
* Renew books
* Check borrowing eligibility
* Automatic policy evaluation

### Policy Management

* Maximum borrowing limit
* Loan duration
* Overdue restrictions
* Fine policies
* Renewal conditions
* Availability requirements

### Intelligent Decision Engine

The system evaluates facts and policies before producing a decision.

**Flow:**

```text
User Request
     ↓
Account & Book Information
     ↓
Policy Evaluation
     ↓
Logical Reasoning
     ↓
Decision
     ↓
Explanation
```

---

## Reasoning Approach

The decision engine is built around a knowledge-based reasoning approach.

The main techniques used are:

* Knowledge-Based Agents
* Propositional Logic
* First-Order Logic
* Forward Chaining
* Backward Chaining
* Resolution
* Knowledge Engineering

These techniques operate behind the application interface to evaluate library policies and determine whether an operation should be approved or rejected.

### Example Rule

```text
IF member has an overdue book
THEN borrowing is restricted
```

Another example:

```text
IF member is within borrowing limit
AND member has no restriction
AND book is available
THEN borrowing is allowed
```

---

## System Architecture

```text
┌──────────────────────────────┐
│          Frontend            │
│      HTML / CSS / JavaScript │
└──────────────┬───────────────┘
               │
               ↓
┌──────────────────────────────┐
│         Flask Backend        │
│       Application Services   │
└──────────────┬───────────────┘
               │
       ┌───────┴────────┐
       ↓                ↓
┌──────────────┐  ┌───────────────┐
│ Decision     │  │    SQLite     │
│ Engine       │  │   Database    │
│   (Python)   │  │               │
└──────────────┘  └───────────────┘
```

### Technology Stack

| Layer           | Technology              |
| --------------- | ----------------------- |
| Frontend        | HTML5, CSS3, JavaScript |
| Backend         | Python Flask            |
| Database        | SQLite                  |
| Decision Engine | Python                  |
| Interface       | Web Browser             |
| Deployment      | Localhost               |

---

## Application Modules

```text
library_platform/
│
├── app.py
├── database.py
├── models.py
├── knowledge_base.py
├── inference_engine.py
│
├── services/
│   ├── member_service.py
│   ├── catalogue_service.py
│   └── circulation_service.py
│
├── templates/
│   ├── base.html
│   ├── overview.html
│   ├── members.html
│   ├── member_detail.html
│   ├── catalogue.html
│   ├── circulation.html
│   └── policies.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
│
└── requirements.txt
```

---

## Main Workflow

### 1. Member Request

A member requests an operation such as borrowing or renewing a book.

### 2. Information Collection

The system retrieves relevant information such as:

* Member status
* Current loans
* Overdue items
* Fines
* Book availability
* Applicable policies

### 3. Rule Evaluation

The decision engine evaluates the available facts against the defined policies.

### 4. Decision

The system determines whether the requested operation is permitted.

### 5. Explanation

The result is displayed with a concise reason.

```text
Approved
✓ Member is eligible
✓ Book is available
✓ No active restrictions
```

or

```text
Not Approved
✕ Member has an overdue item
```

---

## Example Decisions

| Operation | Condition                        | Result       |
| --------- | -------------------------------- | ------------ |
| Borrow    | Member eligible + book available | Approved     |
| Borrow    | Overdue item exists              | Not Approved |
| Borrow    | Borrowing limit reached          | Not Approved |
| Renew     | Renewal conditions satisfied     | Approved     |
| Renew     | Renewal limit reached            | Not Approved |
| Return    | Active loan exists               | Processed    |
| Borrow    | Book unavailable                 | Not Approved |

---

## Installation

### Prerequisites

Make sure the following are installed:

* Python 3.10+
* pip
* Git

### Clone the Repository

```bash
git clone https://github.com/your-username/intelligent-library-rule-management-system.git
```

```bash
cd intelligent-library-rule-management-system
```

### Create a Virtual Environment

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Run the Application

Start the Flask server:

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

The application will be available through your web browser.

---

## Database

The application uses **SQLite** for lightweight local data management.

The database stores information related to:

* Members
* Books
* Loans
* Fines
* Policies

The database can be initialized automatically when the application starts, depending on the project configuration.

---

## Decision Engine

The reasoning process follows a structured approach:

```text
Facts
  ↓
Knowledge Base
  ↓
Rules
  ↓
Inference
  ↓
Decision
```

The engine can use:

### Forward Chaining

Starts with known facts and applies applicable rules to derive new facts.

```text
Fact → Rule → New Fact → Decision
```

### Backward Chaining

Starts with a goal and works backward to determine whether the required conditions are satisfied.

```text
Goal
 ↓
Required Conditions
 ↓
Available Facts
 ↓
Decision
```

### Resolution

Logical clauses can be evaluated to determine whether a conclusion follows from the available knowledge.

---

## Design Principles

The application is designed with the following principles:

* Clean and professional interface
* Centralized policy management
* Consistent decision making
* Explainable results
* Modular backend architecture
* Separation of business logic and presentation
* Lightweight local deployment
* Maintainable code structure

---

## Future Enhancements

Possible future improvements include:

* Multi-branch library support
* Online member accounts
* Email and notification services
* Advanced reporting and analytics
* Cloud deployment
* Role-based access control
* Integration with institutional systems
* Automated reminders for overdue books
* More advanced policy configuration

---

## Project Goal

The goal of the system is to make library operations **faster, more consistent, and easier to manage** by combining conventional library management with structured rule-based decision making.

> **Consistent policies. Faster decisions. Smarter library operations.**

---

## License

This project is available for educational and development purposes.

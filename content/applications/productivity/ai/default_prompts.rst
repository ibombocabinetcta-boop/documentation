==================
AI default prompts
==================

.. |AI| replace:: :abbr:`AI (artificial intelligence)`

*Default prompts* define how |AI| behaves when a user opens a conversation from a specific model in
Odoo. They allow users to:

- Automatically call a specific |AI| agent
- Apply contextual instructions
- Display predefined action buttons
- Adapt |AI| behavior depending on the model

Default prompts are model-specific. This means |AI| can behave differently depending on where it is
launched in the system.

When a user opens an |AI| conversation from a record, Odoo provides the full context of that record
to the |AI| agent. This includes field values and relevant metadata.

A default prompt acts as a configuration layer that determines which agent is called, what
additional instructions are applied, and which predefined actions appear as buttons.

Each conversation is context-bound. When opened from a lead, the |AI| receives information about
that Lead. When opened from an invoice, the |AI| receives accounting context. The conversation is
isolated and reset once closed.

Configuration
=============

Before configuring a default prompt, create or configure the |AI| :ref:`agent <ai/create-agent>` in
the **AI** application.

.. note::
   The **AI** application comes with pre-configured agents, and default prompts. These vary based on
   the other applications installed on the database.

Navigate to :menuselection:`AI app --> Configuration --> Default Prompts` and click :guilabel:`New`.
Create a :guilabel:`Rule Name`, then select an action in the :guilabel:`When users need to` field.

Next, select a model in the :guilabel:`On the Model` field. This controls what records this rule
applies to. For example, if the rule is specific to *Helpdesk* tickets, select *Helpdesk Tickets*
from the drop-down menu. Multiple selections can be made in this field. To allow this rule to be
used by any model, leave the field blank.

In the :guilabel:`Call the Agent` field, select which agent this rule should apply to. Next, add the
:guilabel:`Instructions` for the rule.

.. note::
   While the agent may already have an existing prompt that defines their behavior, the instructions
   in the default prompt define the actions in the context of the current model. See
   :ref:`Understanding AI prompt structure <ai/prompt-structure>` below for additional information.

.. image:: default_prompts/default-prompt-rule.png
   :alt: A default prompt rule record in the AI app.

Buttons
-------

Within each default prompt, buttons can be configured with predefined prompts. While users have the
option to write out a prompt, they can also click one of the buttons to begin the conversation.

On the *Buttons* tab, click :guilabel:`Add a line`, then enter a prompt in the :guilabel:`AI Prompt`
field.

These prompts are then available for a user to select in a conversation.

.. image:: default_prompts/ai-chatter.png
   :alt: AI prompts configured as buttons in a conversation with an agent.

.. _ai/prompt-structure:

Understanding AI prompt structure
=================================

|AI| conversations in Odoo are structured using multiple configuration layers.

- Each :ref:`agent <ai/agents/prompts-in-odoo>` has a prompt that defines the global identity and
  behavior of an AI agent. It is configured directly on the |AI| agent record and applies wherever
  the agent is used. The Agent Prompt defines who the AI is.

- A default prompt configures how an |AI| agent behaves when launched from a specific model. Default
  prompt instructions adapt the agent's behavior to the functional context of the model. The default
  prompt defines how the AI should behave in this specific context.

- Button prompts represent predefined user requests within an |AI| chat window. They appear as
  clickable buttons when a conversation is opened. Button prompts do **not** redefine the agent's
  identity or contextual behavior. Instead, they specify what the |AI| should do at that moment.

.. seealso::
   - :doc:`agents`

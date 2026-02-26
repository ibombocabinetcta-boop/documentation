=============
Toss Payments
=============

`Toss Payments <https://www.tosspayments.com>`_ is a South Korean payment solution provider.
It allows businesses to accept a wide variety of local payment methods.

.. _payment_providers/toss_payments/configure_dashboard:

Configuration on the Toss Payments Merchant Portal
==================================================

#. Contact Toss Payments to `Apply for Service <https://onboarding.tosspayments.com/>`_.
   Through Odoo, you can accept payments using the following methods:

   * `Easy Payment <https://docs.tosspayments.com/resources/glossary/easypay>`_
   * `Bank Transfer <https://docs.tosspayments.com/resources/glossary/transfer-payment>`_
   * `Mobile Payment <https://docs.tosspayments.com/resources/glossary/mobile-payment>`_

   .. note::
       * For :guilabel:`Bank Transfer` transactions, :guilabel:`escrow` (:dfn:`a system where
         funds are held by a trusted third party until the transaction is fulfilled`) will be
         supported in the future.

#. Once approved, access the :guilabel:`Merchant Portal` and click :guilabel:`Developer Center` to
   access the developer center portal. Inside it, select the `Merchant ID` and navigate to
   the :guilabel:`API Key` menu.
#. Inside the :guilabel:`API Individual Integration Key` section, copy the :guilabel:`Client Key`
   and :guilabel:`Secret Key`, and **save this information securely for later**.
#. Once completed, navigate to the :guilabel:`Webhook` menu.
#. Click :guilabel:`Register Webhook`. and enter a preferred name to identify the webhook.
#. In the :guilabel:`URL` field, enter your Odoo database's URL, followed by
   `/payment/toss-payments/webhook`
   (e.g., `https://example.odoo.com/payment/toss-payments/webhook`).

   .. note::
       * The same webhook URL is available for copy and paste from the Toss Payments form view
         in your Odoo database.

#. Ensure the :guilabel:`PAYMENT_STATUS_CHANGED` event is enabled, then save the webhook
   settings.

Configuration on Odoo
=====================

#. :ref:`Navigate to the payment provider Toss Payments <payment_providers/add_new>` and change
   its state to :guilabel:`Enabled`.
#. Fill in the :guilabel:`Client Key` and :guilabel:`Secret Key` fields with the information
   saved at the step :ref:`payment_providers/toss_payments/configure_dashboard`.
#. Configure the rest of the options to your liking.

.. seealso::
   :doc:`../payment_providers`

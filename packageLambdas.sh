#!/bin/sh
echo "packaging complete functions"
mkdir -p complete/packages/lambda_functions
zip -j complete/packages/lambda_functions/Check_Ticket_Status.zip complete/Lambda\ Functions/Check_Ticket_Status/*.py
zip -r -j complete/packages/lambda_functions/lex_custom_lambda.zip complete/Lambda\ Functions/lex_custom_lambda/*.py
zip -r -j complete/packages/lambda_functions/Manage_Ticket.zip complete/Lambda\ Functions/Manage_Ticket/*.py
zip -r -j complete/packages/lambda_functions/Check_Ticket_Status_Validation.zip complete/Lambda\ Functions/Check_Ticket_Status_Validation/*.py
zip -r -j complete/packages/lambda_functions/Hello_Intent.zip complete/Lambda\ Functions/Hello_Intent/*.py
zip -r -j complete/packages/lambda_functions/Thank_You_Intent.zip complete/Lambda\ Functions/Thank_You_Intent/*.py
zip -r -j complete/packages/lambda_functions/FallbackIntent.zip complete/Lambda\ Functions/FallbackIntent/*
zip -r -j complete/packages/lambda_functions/Open_Support_Case_Intent.zip complete/Lambda\ Functions/Open_Support_Case_Intent/*
echo "packaging starter functions"
mkdir -p starter/packages/lambda_functions
zip -j starter/packages/lambda_functions/Check_Ticket_Status.zip starter/Lambda\ Functions/Check_Ticket_Status/*.py
zip -r -j starter/packages/lambda_functions/lex_custom_lambda.zip starter/Lambda\ Functions/lex_custom_lambda/*.py
zip -r -j starter/packages/lambda_functions/Manage_Ticket.zip starter/Lambda\ Functions/Manage_Ticket/*.py
zip -r -j starter/packages/lambda_functions/Check_Ticket_Status_Validation.zip starter/Lambda\ Functions/Check_Ticket_Status_Validation/*.py
zip -r -j starter/packages/lambda_functions/Hello_Intent.zip starter/Lambda\ Functions/Hello_Intent/*.py
zip -r -j starter/packages/lambda_functions/Thank_You_Intent.zip starter/Lambda\ Functions/Thank_You_Intent/*.py
zip -r -j starter/packages/lambda_functions/FallbackIntent.zip starter/Lambda\ Functions/FallbackIntent/*
zip -r -j starter/packages/lambda_functions/Open_Support_Case_Intent.zip starter/Lambda\ Functions/Open_Support_Case_Intent/*
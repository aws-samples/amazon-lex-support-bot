#!/bin/sh
echo "usage: ./deployS3.sh <sourcebucketname> <bucket acl> i.e.: ./deployS3.sh somebucket public-read"

echo "deploying complete/ resources"
aws s3 cp complete/packages/lambda_functions s3://$1/complete/packages/lambda_functions/ --recursive --acl $2
aws s3 cp complete/Lex/SupportBot.json s3://$1/complete/assets/lex/ --acl $2
aws s3 cp complete/templates/lex-supportbot-complete.template s3://$1/complete/ --acl $2
aws s3 cp web s3://$1/complete/assets/web --recursive --acl $2
echo "deploying starter/ resources"
aws s3 cp starter/packages/lambda_functions s3://$1/starter/packages/lambda_functions/ --recursive --acl $2
aws s3 cp starter/Lex/SupportBot.json s3://$1/starter/assets/lex/ --acl $2
aws s3 cp starter/templates/lex-supportbot-starter.template s3://$1/starter/ --acl $2
aws s3 cp web s3://$1/starter/assets/web --recursive --acl $2
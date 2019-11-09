import settings
import makereport










if False:


    #
    # Send email!
    #

    from email.message import EmailMessage
    from email.utils import make_msgid
    import mimetypes

    msg = EmailMessage()

    # generic email headers
    msg['Subject'] = 'Hello there'
    msg['From'] = 'ABCD <abcd@xyz.com>'
    msg['To'] = 'PQRS <pqrs@xyz.com>'

    # set the plain text body
    msg.set_content('This is a plain text body.')

    # now create a Content-ID for the image
    image_cid = make_msgid(domain='xyz.com')
    # if `domain` argument isn't provided, it will
    # use your computer's name

    # set an alternative html body
    msg.add_alternative("""\
    <html>
        <body>
            <p>This is an HTML body.<br>
            It also has an image.
            </p>
            <img src="cid:{image_cid}">
        </body>
    </html>
    """.format(image_cid=image_cid[1:-1]), subtype='html')
    # image_cid looks like <long.random.number@xyz.com>
    # to use it as the img src, we don't need `<` or `>`
    # so we use [1:-1] to strip them off


    # now open the image and attach it to the email
    with open('path/to/image.jpg', 'rb') as img:

        # know the Content-Type of the image
        maintype, subtype = mimetypes.guess_type(img.name)[0].split('/')

        # attach it
        msg.get_payload()[1].add_related(img.read(),
                                            maintype=maintype,
                                            subtype=subtype,
                                            cid=image_cid)


    # the message is ready now
    # you can write it to a file
    # or send it using smtplib